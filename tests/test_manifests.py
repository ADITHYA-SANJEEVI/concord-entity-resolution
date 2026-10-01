from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_final_submission_manifest() -> None:
    manifest = json.loads((ROOT / "archive_manifest" / "final_submission.json").read_text())
    assert manifest["project"] == "Concord"
    assert manifest["public_leaderboard"]["macro_f0_5"] == 0.955136
    assert manifest["public_leaderboard"]["rank"] == 2502
    assert manifest["counts"]["candidate_pairs"] == 87_934_151
    assert manifest["counts"]["accepted_links"] == 5_708_382
    assert manifest["outputs_committed"] is False


def test_model_redistribution_omission_is_explicit() -> None:
    manifest = json.loads((ROOT / "archive_manifest" / "artifacts.json").read_text())
    models = [item for item in manifest["artifacts"] if item["role"] == "trained model"]
    assert len(models) == 2
    assert all(item["represented_in_git"] is False for item in models)
    assert all("redistribution" in item["reason"].lower() for item in models)
