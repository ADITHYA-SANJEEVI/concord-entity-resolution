from __future__ import annotations

import hashlib
import json
from pathlib import Path

from concord.provenance import (
    AMAZON_SUBMISSION_SHA256,
    CANDIDATE_PAIRS_SHA256,
    MATCHING_RESULTS_SHA256,
)


ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "src" / "concord" / "legacy_amazon"


def test_frozen_schema_contract() -> None:
    schema = json.loads((LEGACY / "artifacts" / "ordered_59_feature_schema.json").read_text())
    assert schema["feature_count"] == 59
    assert schema["base_feature_count"] == 55
    assert schema["cross_script_feature_count"] == 4
    assert schema["dtype"] == "float32"
    assert schema["threshold"] == 0.64
    assert len(schema["ordered_features"]) == 59


def test_frozen_model_config_contract() -> None:
    config = json.loads((LEGACY / "artifacts" / "lightgbm_config.json").read_text())
    assert config["n_estimators"] == 600
    assert config["learning_rate"] == 0.05
    assert config["num_leaves"] == 63
    assert config["min_child_samples"] == 100
    assert config["reg_lambda"] == 1.0
    assert config["subsample"] == 1.0
    assert config["colsample_bytree"] == 1.0
    assert config["random_state"] == 42
    assert config["early_stopping"] is False
    assert config["class_weight"] is None


def test_historical_source_hashes() -> None:
    expected = json.loads((ROOT / "archive_manifest" / "source_snapshot.json").read_text())
    for name, digest in expected["files"].items():
        actual = hashlib.sha256((LEGACY / name).read_bytes()).hexdigest()
        assert actual == digest


def test_submission_identities_are_pinned() -> None:
    assert len(AMAZON_SUBMISSION_SHA256) == 64
    assert len(MATCHING_RESULTS_SHA256) == 64
    assert len(CANDIDATE_PAIRS_SHA256) == 64
