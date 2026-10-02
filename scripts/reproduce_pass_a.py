"""Execute the committed P0 fixture; retain manifests and logical repeat identities."""

import argparse
import json
import runpy
import subprocess
import sys
from pathlib import Path

from concord.metadata import read_json, write_json
from concord.storage import write_entities


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    out = Path(args.output)
    if out.exists() and any(out.iterdir()):
        raise ValueError("use a new evidence output directory")
    out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    fixtures = runpy.run_path(str(root / "examples/synthetic/pass_a_fixture.py"))
    records, truth = fixtures["fixture"]()
    write_entities(out / "inputs/entities.parquet", records)
    write_json(out / "inputs/truth.json", truth)
    reports = {}
    for action in ("run", "repeat", "frontier", "lane-rescue", "ablate"):
        directory = out / action
        cmd = [sys.executable, "-m", "concord", "retrieve",
               "run" if action == "repeat" else action,
               "--entities", str(out / "inputs/entities.parquet"),
               "--truth", str(out / "inputs/truth.json"), "--profile", "synthetic",
               "--output", str(directory), "--population", "P0/pass-a-fixture-v1/all-queries",
               "--track", "SYNTHETIC_PUBLIC", "--run-id", f"pass-a-p0-{action}"]
        subprocess.run(cmd, check=True, capture_output=True)
        reports[action] = read_json(directory / "report.json")
    first, repeat = reports["run"], reports["repeat"]
    same = first["candidate_fingerprint"] == repeat["candidate_fingerprint"]
    if not same:
        raise AssertionError("synthetic logical candidates changed across identical runs")
    hrecords, htruth = fixtures["historical_fixture"]()
    write_entities(out / "historical/inputs/entities.parquet", hrecords)
    write_json(out / "historical/inputs/truth.json", htruth)
    cmd = [sys.executable, "-m", "concord", "retrieve", "run",
           "--entities", str(out / "historical/inputs/entities.parquet"),
           "--truth", str(out / "historical/inputs/truth.json"), "--profile", "historical",
           "--output", str(out / "historical/run"),
           "--population", "P0/pass-a-historical-df-fixture-v1/all-queries",
           "--track", "SYNTHETIC_PUBLIC", "--run-id", "pass-a-p0-historical"]
    subprocess.run(cmd, check=True, capture_output=True)
    historical = read_json(out / "historical/run/report.json")
    summary = {"population": first["population"], "candidate_hash_repeat_equal": same,
               "candidate_fingerprint": first["candidate_fingerprint"],
               "reports": {action: f"{action}/report.json" for action in reports},
               "historical_report": "historical/run/report.json",
               "historical_metrics": {key: historical[key] for key in (
                   "queries", "targets", "candidate_pairs", "eligible_cartesian_pairs",
                   "truth_pairs", "truths_recovered", "truth_pair_recall", "reduction_ratio",
                   "density", "zero_candidate_queries", "zero_candidate_rate",
               )},
               "metrics": {key: first[key] for key in (
                   "queries", "targets", "candidate_pairs", "eligible_cartesian_pairs",
                   "truth_pairs", "truths_recovered", "truth_pair_recall", "reduction_ratio",
                   "density", "zero_candidate_queries", "zero_candidate_rate",
                   "recall_at_k_forward_lane_union", "lane_rescue",
               )}}
    write_json(out / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
