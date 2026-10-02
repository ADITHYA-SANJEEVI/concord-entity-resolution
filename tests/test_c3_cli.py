import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from concord.c3_cli import verified_run
from concord.c3_storage import read_stage
from concord.cli import parser
from concord.features.reference import REFERENCE_SCHEMA
from concord.metadata import read_json, validate_manifest, write_json
from concord.provenance import sha256_file

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def c3_reproduction(tmp_path_factory):
    output = tmp_path_factory.mktemp("public-c3") / "run"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run([sys.executable, str(ROOT / "scripts/reproduce_pass_b.py"), "--output", str(output)],
                            cwd=ROOT, env=env, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert json.loads(result.stdout)["resolution_repeat_equal"] is True
    return output


def test_complete_public_c3_cli_and_no_leakage(c3_reproduction):
    root = c3_reproduction
    summary = read_json(root / "summary.json")
    assert summary["model_repeat_equal"] and summary["resolution_repeat_equal"]
    assert summary["feature_schema_sha256"] == REFERENCE_SCHEMA.sha256
    assert 0 < summary["quality"]["test"]["macro_f05"] < 1
    assert summary["quality"]["test"]["query_count"] == 16
    counts = summary["failures"]["test"]["counts"]["FALSE_NEGATIVE"]
    assert all(counts[stage] > 0 for stage in ("RETRIEVAL", "SCORING", "OWNERSHIP", "AMBIGUOUS_OR_INSUFFICIENT_EVIDENCE"))
    assert counts["DECODING"] == 0  # historical baseline has no extra set exclusion
    for file in (root / "fit").glob("*truth*.json"):
        assert all(q.startswith("train-") for q, _ in read_json(file))
    negatives = read_stage(root / "fit/negatives.parquet", "negatives")
    assert all(p.s1_id.startswith("train-") and p.target_id.startswith("train-") for p in negatives)
    metadata = read_json(root / "fit/model_metadata.json")
    assert metadata["training_configuration"]["min_child_samples"] == 100
    assert metadata["training_configuration"]["n_estimators"] == 600
    assert read_json(root / "resolve-test/report.json")["resolution_fingerprint"] == read_json(root / "resolve-repeat/report.json")["resolution_fingerprint"]
    assert all(r["split_fingerprint"] == summary["split_fingerprints"]["test"] for r in read_json(root / "resolve-test/resolution_evidence.json"))
    assert "is_stable" not in (root / "resolve-test/resolution_evidence.json").read_text()
    for filename in ("model-fingerprint", "explain", "export-evidence", "train-calibrate"):
        assert read_json(root / f"logs/{filename}.stdout.json")


def test_manifests_physical_hashes_and_stage_lineage(c3_reproduction):
    manifests = list(c3_reproduction.glob("*/manifest.json"))
    assert len(manifests) == 18
    for path in manifests:
        manifest = verified_run(path.parent)
        validate_manifest(manifest)
        assert manifest["evidence"]["class"] == "D"
        assert manifest["provenance"]["split_fingerprint"] is not None
        for name, artifact in manifest["artifacts"].items():
            assert sha256_file(path.parent / name) == artifact["sha256"]
        assert all(m["producing_run"] == manifest["experiment_id"] for m in manifest["metrics"].values())
    manifest = verified_run(c3_reproduction / "resolve-test")
    a = manifest["artifacts"]
    assert a["features.parquet"]["sha256"] in a["scores.parquet"]["lineage"]["parent_sha256"]
    assert a["scores.parquet"]["sha256"] in a["ownership.parquet"]["lineage"]["parent_sha256"]
    assert a["ownership.parquet"]["sha256"] in a["candidate_dispositions.parquet"]["lineage"]["parent_sha256"]
    assert a["candidate_dispositions.parquet"]["sha256"] in a["resolutions.parquet"]["lineage"]["parent_sha256"]
    assert a["resolutions.parquet"]["sha256"] in a["resolution_evidence.json"]["lineage"]["parent_sha256"]


@pytest.mark.parametrize("verb,action", [("train", "fit"), ("train", "negatives"), ("train", "calibrate"),
    ("train", "fingerprint"), ("resolve", "run"), ("resolve", "explain"), ("resolve", "export-evidence"),
    ("evaluate", "quality"), ("evaluate", "calibration"), ("evaluate", "failures"), ("evaluate", "policy")])
def test_c3_cli_rejects_missing_required_arguments(verb, action):
    with pytest.raises(SystemExit) as result:
        parser().parse_args([verb, action])
    assert result.value.code == 2


@pytest.mark.parametrize("arguments", [["benchmark"], ["evaluate", "stability"], ["evaluate", "drift"],
                                     ["retrieve", "challenge-transliteration"], ["retrieve", "challenge-adaptive-k"]])
def test_c4_commands_not_exposed(arguments):
    with pytest.raises(SystemExit) as result:
        parser().parse_args(arguments)
    assert result.value.code == 2


def test_invalid_parent_hash_and_failed_c3_run_are_retained(c3_reproduction, tmp_path):
    root = c3_reproduction
    out = tmp_path / "failed-evaluation"
    truth = tmp_path / "bad-truth.json"
    write_json(truth, [["unknown query", "unknown target"]])
    arguments = [sys.executable, "-m", "concord", "evaluate", "quality", "--resolution-run", str(root / "resolve-test"),
                 "--truth", str(truth), "--output", str(out), "--population", "P0/invalid", "--track", "SYNTHETIC_PUBLIC", "--run-id", "invalid"]
    failed = subprocess.run(arguments, cwd=ROOT, capture_output=True, check=False)
    assert failed.returncode == 2
    manifest = read_json(out / "manifest.json")
    validate_manifest(manifest)
    assert manifest["disposition"] == "FAILED" and manifest["evidence"]["notes"]
    before = (out / "manifest.json").read_bytes()
    assert subprocess.run(arguments, cwd=ROOT, capture_output=True, check=False).returncode == 2
    assert (out / "manifest.json").read_bytes() == before
    # Do not mutate the valid fixture artifacts while other tests consume them.
    copied = tmp_path / "tampered"
    copied.mkdir()
    original = verified_run(root / "resolve-test")
    artifact = next(iter(original["artifacts"]))
    write_json(copied / "manifest.json", original)
    (copied / artifact).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="hash mismatch"):
        verified_run(copied)
