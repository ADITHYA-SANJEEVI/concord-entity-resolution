"""Public C4 CLI reproduction, retained logs and verified physical artifacts."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from concord.c3_cli import verified_run
from concord.metadata import write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--sizes", default="128,512,2048")
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = Path(args.output).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError("use a new directory; retained evidence is never overwritten")
    (out / "logs").mkdir(parents=True, exist_ok=True)
    for action, extra in (("public", ()), ("scale", ("--model-run", str(out / "public"), "--sizes", args.sizes, "--repetitions", str(args.repetitions)))):
        result = subprocess.run([sys.executable, "-m", "concord", "benchmark", action,
            "--output", str(out / action), "--population", "P0/multilingual-c4/" + action,
            "--track", "SYNTHETIC_PUBLIC", "--run-id", "pass-c-" + action, *extra], cwd=root, capture_output=True, check=False)
        (out / f"logs/{action}.stdout.json").write_bytes(result.stdout)
        (out / f"logs/{action}.stderr.txt").write_bytes(result.stderr)
        if result.returncode:
            raise RuntimeError(f"{action} failed ({result.returncode}); inspect retained stderr")
        json.loads(result.stdout)
    manifests = {action: verified_run(out / action) for action in ("public", "scale")}
    summary = {"schema_version": "concord.pass-c-reproduction.v1", "evidence_class": "D",
               "verified_artifacts": {k: len(m["artifacts"]) for k, m in manifests.items()},
               "producing_git": {k: m["git"] for k, m in manifests.items()},
               "artifact_bytes": {k: sum(a["bytes"] for a in m["artifacts"].values()) for k, m in manifests.items()},
               "claim_boundary": "Invented P0 public experiments and current measured scale; reference/private/production claims excluded."}
    write_json(out / "reproduction.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
