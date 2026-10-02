import runpy
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import pytest
from test_c3_resolution import SHA, score

from concord.c3_contracts import FEATURE_VERSION, FailureAttribution, FeatureRow, ResolutionDecision
from concord.c3_storage import read_stage, write_stage
from concord.contracts import EntityRecord, LaneEvidence, RetrievalCandidate
from concord.features.reference import REFERENCE_SCHEMA
from concord.identity import canonical_records, dataset_fingerprint
from concord.inference.resolution import decode, global_ownership
from concord.metadata import content_sha256
from concord.modeling.scorer import LightGBMScorer, ModelConfig, model_metadata, score_features
from concord.modeling.training import NegativeConfig, SplitGroup, SplitPlan, mine_negatives

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def mining_fixture():
    records = canonical_records(EntityRecord(f"{role}-{suffix}", source, "Invented", "18 Road", None)
                                for role in ("train", "calibration", "test")
                                for suffix, source in (("q", "S1"), ("true", "S2"), ("near", "S2"), ("far", "S3")))
    groups = tuple(SplitGroup(role, role, tuple((r.source, r.entity_id) for r in records if r.entity_id.startswith(role + "-")))
                   for role in ("train", "calibration", "test"))
    plan = SplitPlan(dataset_fingerprint(records), groups)
    selected = plan.select(records, "train")
    candidates = tuple(RetrievalCandidate("train-q", f"train-{target}", source, None, 1,
                                        (LaneEvidence("name", 1, value),))
                       for target, source, value in (("true", "S2", .8), ("near", "S2", .9), ("far", "S3", .3)))
    return records, selected, plan, candidates


def test_retrieval_only_hard_negatives_deterministic_provenance(mining_fixture):
    _, records, plan, candidates = mining_fixture
    config = NegativeConfig(max_negatives_per_query=1)
    truth = (("train-q", "train-true"),)
    a = mine_negatives(records, candidates, truth, plan, "train", SHA, SHA, config)
    b = mine_negatives(tuple(reversed(records)), tuple(reversed(candidates)), truth, plan, "train", SHA, SHA, config)
    assert a == b
    assert {(p.target_id, p.label) for p in a} == {("train-true", 1), ("train-near", 0)}
    assert all((p.s1_id, p.target_id) in {(c.s1_id, c.target_id) for c in candidates} for p in a)
    assert all(p.split_fingerprint == plan.split_sha256("train") and p.negative_config_sha256 == config.sha256 for p in a)
    assert a[0].reason == "retrieved_not_labelled_truth_top_similarity"
    assert replace(config, seed=43).sha256 != config.sha256
    # A truth outside the bounded graph is counted upstream, never inserted as a training pair.
    without = tuple(c for c in candidates if c.target_id != "train-true")
    assert all(p.label == 0 for p in mine_negatives(records, without, truth, plan, "train", SHA, SHA, config))


@pytest.mark.parametrize("violation", ["heldout_truth", "heldout_candidate", "wrong_records", "eval_role", "overlap"])
def test_leakage_rejected_by_construction(violation, mining_fixture):
    full, records, plan, candidates = mining_fixture
    truth = (("train-q", "train-true"),)
    with pytest.raises(ValueError):
        if violation == "heldout_truth":
            mine_negatives(records, candidates, (("test-q", "test-true"),), plan, "train", SHA, SHA)
        elif violation == "heldout_candidate":
            mine_negatives(records, candidates + (replace(candidates[0], target_id="test-true"),), truth, plan, "train", SHA, SHA)
        elif violation == "wrong_records":
            mine_negatives(full, candidates, truth, plan, "train", SHA, SHA)
        elif violation == "eval_role":
            mine_negatives(plan.select(full, "test"), (), (), plan, "test", SHA, SHA)
        else:
            group = replace(plan.groups[1], members=tuple(sorted(plan.groups[1].members + (plan.groups[0].members[0],))))
            replace(plan, groups=(plan.groups[0], group, plan.groups[2]))


def test_split_plan_committed_membership_and_hash_sensitivity():
    fixture = runpy.run_path(str(ROOT / "examples/synthetic/pass_b_fixture.py"))
    records, _ = fixture["fixture"]()
    plan = fixture["split_plan"]()
    assert plan.dataset_fingerprint == dataset_fingerprint(records)
    sets = [set(g.members) for g in plan.groups]
    assert not (sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2])
    assert len(sets[0]) == 720 and len(sets[1]) == 36 and len(sets[2]) == 37
    assert len({plan.split_sha256(g.name) for g in plan.groups}) == 3
    with pytest.raises(ValueError, match="different logical"):
        plan.select(records[:-1], "train")
    changed = replace(plan.groups[0], name="renamed-training")
    assert replace(plan, groups=(changed, *plan.groups[1:])).sha256 != plan.sha256


@pytest.fixture(scope="module")
def fitted_scorer():
    rng = np.random.default_rng(2026)
    X = rng.random((400, 59), dtype=np.float32)
    y = np.repeat((0, 1), 200)
    X[:, 0] = y
    scorer = LightGBMScorer().fit(X, y)
    return scorer, X, y


def test_reference_model_repeats_and_identity_is_not_a_path(fitted_scorer, tmp_path):
    scorer, X, y = fitted_scorer
    repeated = LightGBMScorer().fit(X.copy(), y.copy())
    assert scorer.fingerprint() == repeated.fingerprint()
    assert np.array_equal(scorer.predict_proba(X), repeated.predict_proba(X))
    params = scorer.get_params()
    assert (params["n_estimators"], params["learning_rate"], params["num_leaves"], params["reg_lambda"]) == (600, .05, 63, 1.)
    assert scorer.config.seed_recovery == "DEFAULTED_TO_42_NO_PRIOR_VALUE_FOUND"
    metadata = model_metadata(scorer, SHA, SHA, SHA, SHA, SHA, SHA, SHA)
    assert "path" not in metadata
    assert metadata["feature_schema_sha256"] == REFERENCE_SCHEMA.sha256
    different = model_metadata(scorer, SHA, "0" * 64, SHA, SHA, SHA, SHA, SHA)
    assert different["model_identity_sha256"] != metadata["model_identity_sha256"]
    path = tmp_path / "model.txt"
    scorer.save(path)
    loaded = LightGBMScorer.load(path, metadata)
    assert np.array_equal(scorer.predict_proba(X), loaded.predict_proba(X))
    with pytest.raises(ValueError, match="schema"):
        LightGBMScorer.load(path, metadata | {"feature_schema_sha256": "0" * 64})
    with pytest.raises(ValueError, match="metadata identity"):
        LightGBMScorer.load(path, metadata | {"dataset_fingerprint": "0" * 64})
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="artifact hash"):
        LightGBMScorer.load(path, metadata)


def test_scorer_schema_input_and_class_constraints(fitted_scorer):
    scorer, X, _ = fitted_scorer
    for bad in (np.zeros((2, 58)), np.ones(59), np.full((2, 59), np.nan)):
        with pytest.raises(ValueError):
            scorer.predict_proba(bad)
    assert scorer.predict_proba(np.empty((0, 59))).shape == (0,)
    with pytest.raises(ValueError, match="both binary"):
        LightGBMScorer().fit(X, np.zeros(len(X)))
    with pytest.raises(ValueError, match="not fitted"):
        LightGBMScorer().predict_proba(X)
    with pytest.raises(ValueError):
        ModelConfig(learning_rate=.1)


def test_scorer_interface_isolated_with_model_agnostic_fake():
    class FakeScorer:
        def predict_proba(self, X):
            assert X.dtype == np.float32
            return np.full(len(X), .75)

        def fingerprint(self):
            return SHA

    row = FeatureRow("opaque q", "opaque t", (0.,) * 59, FEATURE_VERSION, REFERENCE_SCHEMA.sha256)
    candidate = RetrievalCandidate("opaque q", "opaque t", "S3", None, 1, (LaneEvidence("name", 1, .2),))
    scores = score_features((row,), (candidate,), FakeScorer(), model_version="test.numeric-contract.v1")
    assert scores[0].score == .75 and scores[0].target_source == "S3"
    assert scores[0].model_version == "test.numeric-contract.v1"
    assert set(asdict(scores[0])) == {"s1_id", "target_id", "target_source", "score", "model_sha256", "model_version"}
    with pytest.raises(ValueError, match="schema mismatch"):
        score_features((replace(row, schema_sha256="0" * 64),), (candidate,), FakeScorer())
    with pytest.raises(ValueError, match="bounded"):
        score_features((row,), (), FakeScorer())


@pytest.mark.parametrize("stage", ["features", "scores", "ownership", "candidate_dispositions", "resolutions", "failure_attribution", "negatives"])
def test_typed_stage_round_trip_and_empty_tables(stage, mining_fixture, tmp_path):
    _, records, plan, candidates = mining_fixture
    scored = (score("q", "t", .8),)
    ownership = global_ownership(scored)
    dispositions, decisions = decode(ownership, ("q", "zero"))
    values = {
        "features": (FeatureRow("q", "t", (.123456789,) * 59, FEATURE_VERSION, REFERENCE_SCHEMA.sha256),),
        "scores": scored, "ownership": ownership, "candidate_dispositions": dispositions, "resolutions": decisions,
        "failure_attribution": (FailureAttribution("q", "t", "FALSE_NEGATIVE", "SCORING", ("SINGLE_LANE",),
                                                 (("score", .1), ("reason", None))),),
        "negatives": mine_negatives(records, candidates, (("train-q", "train-true"),), plan, "train", SHA, SHA),
    }
    for rows in (values[stage], ()):
        path = tmp_path / f"{stage}.parquet"
        write_stage(path, stage, rows)
        assert read_stage(path, stage) == rows
    path = tmp_path / "wrong-schema.parquet"
    write_stage(path, stage, values[stage])
    table = pq.read_table(path)
    pq.write_table(table.replace_schema_metadata({}), path)
    with pytest.raises(ValueError, match="schema/version"):
        read_stage(path, stage)


def test_reject_invalid_resolution_and_feature_storage(tmp_path):
    with pytest.raises(ValueError, match="duplicate"):
        write_stage(tmp_path / "r.parquet", "resolutions", (ResolutionDecision("q", (), "zero_match"),) * 2)
    row = FeatureRow("q", "t", (0.,) * 59, FEATURE_VERSION, "0" * 64)
    with pytest.raises(ValueError, match="schema mismatch"):
        write_stage(tmp_path / "f.parquet", "features", (row,))
    assert content_sha256(asdict(NegativeConfig())) == NegativeConfig().sha256
