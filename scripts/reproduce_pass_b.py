"""Execute public C3 through gated CLI surfaces; retain artifacts, logs and provenance."""

import argparse
import json
import runpy
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from concord.metadata import read_json, write_json
from concord.storage import write_entities


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    out = Path(args.output)
    if out.exists() and any(out.iterdir()):
        raise ValueError("use a new output directory; previous runs are retained")
    out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    fixture = runpy.run_path(str(root / "examples/synthetic/pass_b_fixture.py"))
    records, truths = fixture["fixture"]()
    plan = fixture["split_plan"]()
    write_entities(out / "inputs/entities.parquet", records)
    write_json(out / "inputs/splits.json", asdict(plan))
    write_json(out / "inputs/ambiguities.json", fixture["ambiguity_annotations"]())

    def execute(name, *arguments):
        result = subprocess.run([sys.executable, "-m", "concord", *map(str, arguments)],
                                cwd=root, capture_output=True, check=False)
        logs = out / "logs"
        logs.mkdir(exist_ok=True)
        (logs / f"{name}.stderr.txt").write_bytes(result.stderr)
        (logs / f"{name}.stdout.json").write_bytes(result.stdout)
        if result.returncode:
            raise RuntimeError(f"{name} failed ({result.returncode}); see {logs / (name + '.stderr.txt')}")
        return json.loads(result.stdout)

    execute("inspect", "inspect", "fingerprint", "--entities", out / "inputs/entities.parquet")
    for group in plan.groups:
        selected = plan.select(records, group.name)
        write_entities(out / f"inputs/{group.name}.parquet", selected)
        write_json(out / f"inputs/{group.name}-truth.json", truths[group.role])
        execute(f"retrieve-{group.name}", "retrieve", "run", "--entities", out / f"inputs/{group.name}.parquet",
                "--profile", "synthetic", "--output", out / f"retrieval-{group.name}",
                "--population", f"P0/pass-b-v1/{group.name}", "--track", "SYNTHETIC_PUBLIC",
                "--run-id", f"pass-b-retrieval-{group.name}")
    training_args = ("--entities", out / "inputs/entities.parquet", "--split-plan", out / "inputs/splits.json",
                     "--split", "train", "--retrieval-run", out / "retrieval-train",
                     "--truth", out / "inputs/train-truth.json", "--population", "P0/pass-b-v1/train",
                     "--track", "SYNTHETIC_PUBLIC")
    execute("negatives", "train", "negatives", *training_args, "--output", out / "negatives", "--run-id", "pass-b-negatives")
    training = execute("fit", "train", "fit", *training_args, "--output", out / "fit", "--run-id", "pass-b-fit")
    repeated = execute("fit-repeat", "train", "fit", *training_args, "--output", out / "fit-repeat", "--run-id", "pass-b-fit-repeat")
    if training["model_sha256"] != repeated["model_sha256"]:
        raise AssertionError("reference training did not reproduce within this platform")
    execute("model-fingerprint", "train", "fingerprint", "--model-run", out / "fit")
    resolution = {}
    for group in ("calibration", "test"):
        resolve_args = ("--entities", out / "inputs/entities.parquet", "--split-plan", out / "inputs/splits.json",
                        "--split", group, "--retrieval-run", out / f"retrieval-{group}", "--model-run", out / "fit",
                        "--population", f"P0/pass-b-v1/{group}", "--track", "SYNTHETIC_PUBLIC")
        resolution[group] = execute(f"resolve-{group}", "resolve", "run", *resolve_args,
                                    "--output", out / f"resolve-{group}", "--run-id", f"pass-b-resolve-{group}")
        if group == "test":
            repeat = execute("resolve-repeat", "resolve", "run", *resolve_args,
                             "--output", out / "resolve-repeat", "--run-id", "pass-b-resolve-repeat")
            for key in ("resolution_fingerprint", "scored_predictions_fingerprint"):
                if repeat[key] != resolution[group][key]:
                    raise AssertionError(f"repeated {key} changed")
        for action in ("quality", "calibration", "failures", "policy"):
            evaluation_args = ("--resolution-run", out / f"resolve-{group}", "--truth", out / f"inputs/{group}-truth.json",
                               "--output", out / f"evaluate-{group}-{action}", "--population", f"P0/pass-b-v1/{group}",
                               "--track", "SYNTHETIC_PUBLIC", "--run-id", f"pass-b-evaluate-{group}-{action}")
            if group == "test":
                evaluation_args += ("--ambiguities", out / "inputs/ambiguities.json")
            execute(f"evaluate-{group}-{action}", "evaluate", action, *evaluation_args)
    execute("train-calibrate", "train", "calibrate", "--resolution-run", out / "resolve-calibration",
            "--truth", out / "inputs/calibration-truth.json", "--output", out / "train-calibrate",
            "--population", "P0/pass-b-v1/calibration", "--track", "SYNTHETIC_PUBLIC", "--run-id", "pass-b-train-calibrate")
    explanation = execute("explain", "resolve", "explain", "--resolution-run", out / "resolve-test", "--s1-id", "test-amb-z")
    execute("export-evidence", "resolve", "export-evidence", "--resolution-run", out / "resolve-test")
    summary = {"schema_version": "concord.pass-b-reproduction.v1", "evidence_class": "D",
               "dataset_fingerprint": plan.dataset_fingerprint, "split_plan_sha256": plan.sha256,
               "split_fingerprints": {g.name: plan.split_sha256(g.name) for g in plan.groups},
               "feature_schema_sha256": training["feature_schema_sha256"], "training": training,
               "model_repeat_equal": True, "resolution_repeat_equal": True, "resolution": resolution,
               "quality": {g: read_json(out / f"evaluate-{g}-quality/quality.json") for g in ("calibration", "test")},
               "calibration": {g: read_json(out / f"evaluate-{g}-calibration/calibration.json") for g in ("calibration", "test")},
               "failures": {g: read_json(out / f"evaluate-{g}-failures/failures.json") for g in ("calibration", "test")},
               "evidence_example": explanation,
               "claim_boundary": "Public invented P0 only; no private parity, leaderboard, scale, WDC or C4 stability claim."}
    write_json(out / "summary.json", summary)
    print(json.dumps({"model_repeat_equal": True, "resolution_repeat_equal": True,
                      "test_quality": summary["quality"]["test"], "test_failures": summary["failures"]["test"]["counts"]}, indent=2))


if __name__ == "__main__":
    main()
