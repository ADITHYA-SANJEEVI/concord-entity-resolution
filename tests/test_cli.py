import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from concord.identity import dataset_fingerprint
from concord.metadata import (
    ArtifactLineage,
    read_json,
    validate_lineage,
    validate_manifest,
    write_json,
)
from concord.provenance import sha256_file
from concord.storage import read_candidates, write_entities

ROOT = Path(__file__).resolve().parents[1]


def invoke(*args):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run([sys.executable, "-m", "concord", *map(str, args)],
                          cwd=ROOT, env=env, capture_output=True, check=False)


@pytest.mark.parametrize("action", ["profile", "schema", "fingerprint"])
def test_inspect_cli(action, public_fixture, tmp_path):
    records, _ = public_fixture
    path = tmp_path / "entities.parquet"
    write_entities(path, records)
    split = {"name": "dev", "purpose": "retrieval", "members": [["S1", records[0].entity_id]]}
    write_json(tmp_path / "split.json", split)
    result = invoke("inspect", action, "--entities", path, "--split-json", tmp_path / "split.json")
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    if action == "fingerprint":
        assert report["dataset_fingerprint"] == dataset_fingerprint(records)
        assert len(report["split_fingerprint"]) == 64
    elif action == "schema":
        assert report["valid"] and report["rows"] == len(records)
    else:
        assert report["fields"]["business_name"]["missing"] > 0


@pytest.mark.parametrize("action", ["run", "frontier", "lane-rescue", "ablate"])
def test_retrieve_cli_manifest_freeze_and_lineage(action, public_fixture, tmp_path):
    records, truth = public_fixture
    entities = tmp_path / "entities.parquet"
    write_entities(entities, records)
    write_json(tmp_path / "truth.json", truth)
    out = tmp_path / action
    result = invoke("retrieve", action, "--entities", entities, "--truth", tmp_path / "truth.json",
                    "--profile", "synthetic", "--output", out, "--population", "P0/test-v1",
                    "--track", "SYNTHETIC_PUBLIC", "--run-id", "test-cli", "--ks", "1,2,5")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)
    manifest = read_json(out / "manifest.json")
    validate_manifest(manifest)
    assert manifest["disposition"] == "COMPLETED"
    assert manifest["evidence"]["class"] == "D"
    freeze = read_json(out / "retrieval_freeze.json")
    assert freeze["labels_accessed"] is False
    candidates = read_candidates(out / "retrieval_candidates.parquet")
    assert len(candidates) == read_json(out / "report.json")["candidate_pairs"]
    lineage = []
    for name, record in manifest["artifacts"].items():
        assert record["sha256"] == sha256_file(out / name)
        fields = dict(record["lineage"])
        fields["parent_sha256"] = tuple(fields["parent_sha256"])
        lineage.append(ArtifactLineage(**fields))
    validate_lineage(tuple(lineage))
    assert all(m["population"] == "P0/test-v1" and m["producing_run"] == "test-cli"
               for m in manifest["metrics"].values())
    assert asdict(lineage[0])["evidence_class"] == "D"
    if action == "frontier":
        report = read_json(out / "report.json")
        assert len(report["frontier"]["points"]) == 3
        assert all((out / f"frontier_{i}_candidates.parquet").exists() for i in range(3))
        assert (out / "frontier.svg").read_text(encoding="utf-8").find("<svg") >= 0


def test_cli_retains_failed_run(public_fixture, tmp_path):
    records, _ = public_fixture
    path = tmp_path / "entities.parquet"
    write_entities(path, records)
    write_json(tmp_path / "bad-truth.json", [["unknown", "target"]])
    out = tmp_path / "failed"
    result = invoke("retrieve", "run", "--entities", path, "--truth", tmp_path / "bad-truth.json",
                    "--profile", "synthetic", "--output", out, "--population", "P0/invalid",
                    "--track", "SYNTHETIC_PUBLIC", "--run-id", "failed")
    assert result.returncode == 2
    manifest = read_json(out / "manifest.json")
    validate_manifest(manifest)
    assert manifest["disposition"] == "FAILED" and manifest["evidence"]["notes"]
    assert (out / "retrieval_freeze.json").exists()
    assert not (out / "report.json").exists()
    assert not manifest["metrics"]
    before = (out / "manifest.json").read_bytes()
    again = invoke("retrieve", "run", "--entities", path, "--output", out,
                   "--population", "P0/invalid", "--track", "SYNTHETIC_PUBLIC", "--run-id", "again")
    assert again.returncode == 2
    assert before == (out / "manifest.json").read_bytes()


def test_cli_rejects_invalid_split(public_fixture, tmp_path):
    records, _ = public_fixture
    write_entities(tmp_path / "entities.parquet", records)
    write_json(tmp_path / "split.json", {"name": "x", "purpose": "x", "members": [["S1", "x"]]})
    result = invoke("inspect", "fingerprint", "--entities", tmp_path / "entities.parquet",
                    "--split-json", tmp_path / "split.json")
    assert result.returncode == 2


def test_public_existing_tsv_paths():
    result = invoke("inspect", "profile", "--source1", ROOT / "examples/synthetic/source1.tsv",
                    "--source2", ROOT / "examples/synthetic/source2.tsv",
                    "--source3", ROOT / "examples/synthetic/source3.tsv")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["rows"] == 6


def test_later_gates_absent():
    for verb in ("train", "resolve", "evaluate", "benchmark"):
        assert invoke(verb).returncode == 2
