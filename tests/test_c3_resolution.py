from dataclasses import FrozenInstanceError, fields, replace
from itertools import permutations

import pytest

from concord.c3_contracts import (
    CandidateDisposition,
    FailureAttribution,
    OwnershipResult,
    ResolutionDecision,
    ResolutionEvidenceRecord,
    ScoredCandidate,
)
from concord.contracts import LaneEvidence, RetrievalCandidate
from concord.evaluation.failures import attribute_failures, attribute_stage
from concord.evaluation.quality import calibration_report, quality_report, set_metrics
from concord.inference.resolution import DecoderConfig, decode, evidence_capsules, global_ownership

SHA, COMMIT = "a" * 64, "b" * 40


def score(q, target, value, source="S2"):
    return ScoredCandidate(q, target, source, value, SHA)


def candidate(q, target, lanes=1):
    names = ("name", "compact", "address", "combined", "reverse")[:lanes]
    return RetrievalCandidate(q, target, "S2", None, (1 << lanes) - 1,
                              tuple(LaneEvidence(name, 1, .5) for name in names))


def test_global_ownership_order_rivals_and_all_permutations():
    scores = (score("z", "opaque t", .9), score("a", "opaque t", .9), score("m", "opaque t", .7), score("x", "solo", .1))
    expected = global_ownership(scores)
    for order in permutations(scores):
        assert global_ownership(order) == expected
    owners = {(o.s1_id, o.target_id): o for o in expected}
    winner = owners["a", "opaque t"]
    assert winner.is_owner and winner.owner_rank == 1
    assert (winner.rival_s1_id, winner.rival_score, winner.rival_margin) == ("z", .9, 0.)
    assert owners["z", "opaque t"].owner_rank == 2
    assert owners["m", "opaque t"].rival_margin == pytest.approx(-.2)
    assert owners["x", "solo"].rival_margin is None
    assert global_ownership(()) == ()
    with pytest.raises(ValueError, match="duplicate"):
        global_ownership(scores + (scores[0],))
    with pytest.raises(ValueError, match="source"):
        global_ownership((score("a", "t", .9), score("b", "t", .8, "S3")))
    with pytest.raises(ValueError, match="one model"):
        global_ownership((scores[0], replace(scores[1], model_sha256="0" * 64)))


@pytest.mark.parametrize("value,expected", [(.639999999999, False), (.640, True), (.640000000001, True), (0., False), (1., True)])
def test_frozen_threshold_boundary(value, expected):
    dispositions, decisions = decode(global_ownership((score("q", "t", value),)), ("q",))
    assert dispositions[0].accepted is expected
    assert decisions[0].accepted_targets == (("t",) if expected else ())
    assert dispositions[0].threshold == .640
    assert dispositions[0].threshold_margin == value - .640


def test_zero_one_many_rejections_and_forged_ownership():
    ownership = global_ownership((score("a", "t", .9), score("z", "t", .8), score("a", "u", .7),
                                  score("single", "s", .640), score("low", "l", .63)))
    dispositions, decisions = decode(ownership, ("z", "a", "empty", "single", "low"))
    by_id = {d.s1_id: d for d in decisions}
    assert by_id["a"].decision_type == "multi_match" and by_id["a"].accepted_targets == ("t", "u")
    assert by_id["single"].decision_type == "single_match"
    assert by_id["empty"].accepted_targets == ()
    assert {d.rejection_reason for d in dispositions} == {"NONE", "LOST_OWNERSHIP", "BELOW_THRESHOLD"}
    accepted = [d.target_id for d in dispositions if d.accepted]
    assert len(accepted) == len(set(accepted))
    assert decode((), ("empty",))[1] == (ResolutionDecision("empty", (), "zero_match"),)
    with pytest.raises(ValueError):
        DecoderConfig(threshold=.63)
    with pytest.raises(ValueError, match="arbitration"):
        decode((OwnershipResult("z", "t", .9, True, 1, "a", .9, 0.),
                OwnershipResult("a", "t", .9, False, 2, "z", .9, 0.)), ("a", "z"))
    with pytest.raises(ValueError, match="population"):
        decode(ownership, ("a",))
    with pytest.raises(ValueError):
        replace(dispositions[0], rejection_reason="SET_POLICY")


def test_stage_separation_and_probability_validation():
    assert not {"is_owner", "accepted", "rejection_reason", "decoder_version"} & {f.name for f in fields(ScoredCandidate)}
    assert "accepted" not in {f.name for f in fields(OwnershipResult)}
    assert "is_stable" not in {f.name for f in fields(ResolutionEvidenceRecord)}
    scored = score("q", "t", .8)
    with pytest.raises(FrozenInstanceError):
        scored.score = .9
    for invalid in (float("nan"), float("inf"), -.1, 1.1, True):
        with pytest.raises(ValueError):
            replace(scored, score=invalid)
    with pytest.raises(ValueError):
        replace(scored, s1_id=" ")
    with pytest.raises(ValueError):
        replace(scored, target_source="S1")
    with pytest.raises(ValueError):
        replace(scored, model_sha256="local/path")
    with pytest.raises(ValueError):
        ResolutionDecision("q", ("z", "a"), "multi_match")
    with pytest.raises(ValueError):
        ResolutionDecision("q", ["t"], "single_match")
    with pytest.raises(ValueError):
        CandidateDisposition("q", "t", .99, False, .640, .35, True, "NONE")


@pytest.mark.parametrize("truth,prediction,expected", [
    ((), (), (1., 1., 1., 1.)), ((), ("a",), (0., 1., 0., 0.)),
    (("a",), (), (0., 0., 0., 0.)), (("a",), ("a",), (1., 1., 1., 1.)),
    (("a", "b"), ("b", "c"), (.5, .5, .5, 0.)),
    (("a", "b"), ("a",), (1., .5, 5 / 6, 0.)),
])
def test_per_query_set_semantics(truth, prediction, expected):
    result = set_metrics(frozenset(truth), frozenset(prediction))
    assert (result["precision"], result["recall"], result["f05"], result["exact_set"]) == pytest.approx(expected)


def test_macro_population_cohorts_and_exclusivity():
    decisions = (ResolutionDecision("zero", (), "zero_match"), ResolutionDecision("one", (), "zero_match"),
                 ResolutionDecision("many", ("b",), "single_match"))
    report = quality_report(("zero", "one", "many"), (("one", "a"), ("many", "b"), ("many", "c")), decisions, "P0/test")
    assert report["macro_f05"] == pytest.approx((1 + 0 + 5 / 6) / 3)
    assert report["macro_precision"] == pytest.approx(2 / 3)
    assert report["macro_recall"] == .5
    assert report["exact_set_accuracy"] == pytest.approx(1 / 3)
    assert all(cohort["query_count"] == 1 for cohort in report["cohorts"].values())
    assert quality_report((), (), (), "P0/empty")["macro_f05"] is None
    with pytest.raises(ValueError, match="multiple"):
        quality_report(("a", "b"), (), (ResolutionDecision("a", ("t",), "single_match"),
                       ResolutionDecision("b", ("t",), "single_match")), "P0/test")


@pytest.mark.parametrize("retrieved,value,owner,expected", [(False, None, None, "RETRIEVAL"),
    (True, .63, True, "SCORING"), (True, .63, False, "SCORING"), (True, .640, False, "OWNERSHIP"),
    (True, .8, True, "DECODING")])
def test_false_negative_precedence(retrieved, value, owner, expected):
    assert attribute_stage(error_type="FALSE_NEGATIVE", retrieved=retrieved, score=value,
                           is_owner=owner, emitted=False) == expected


@pytest.mark.parametrize("value,expected", [(.9, "SCORING"), (.640, "SCORING"), (.63, "DECODING")])
def test_false_positive_policy(value, expected):
    assert attribute_stage(error_type="FALSE_POSITIVE", retrieved=True, score=value, is_owner=True, emitted=True) == expected


def test_genuine_ambiguity_and_missing_pipeline_are_distinct():
    assert attribute_stage(error_type="FALSE_NEGATIVE", retrieved=True, score=.9, is_owner=False, emitted=False,
                           ambiguity_reason="two labels require mutually exclusive owners") == "AMBIGUOUS_OR_INSUFFICIENT_EVIDENCE"
    with pytest.raises(ValueError, match="incomplete"):
        attribute_stage(error_type="FALSE_NEGATIVE", retrieved=True, score=None, is_owner=None, emitted=False)
    with pytest.raises(ValueError, match="genuine"):
        attribute_stage(error_type="FALSE_NEGATIVE", retrieved=False, score=None, is_owner=None, emitted=False, ambiguity_reason="")
    with pytest.raises(ValueError):
        FailureAttribution("q", "t", "FALSE_NEGATIVE", "RETRIEVAL", (), (("mutable", {}),))


def test_decoding_attribution_detects_mis_emitted_artifact_without_set_policy():
    candidates, scores = (candidate("q", "t"),), (score("q", "t", .9),)
    ownership = global_ownership(scores)
    dispositions, _ = decode(ownership, ("q",))
    # Simulated artifact emission defect, not a new SET_POLICY exclusion.
    decisions = (ResolutionDecision("q", (), "zero_match"),)
    failures = attribute_failures(("q",), (("q", "t"),), candidates, scores, ownership, dispositions, decisions)
    assert failures[0].failure_stage == "DECODING"
    assert dispositions[0].accepted and dispositions[0].rejection_reason == "NONE"
    with pytest.raises(ValueError, match="actual frozen"):
        evidence_capsules(candidates, scores, ownership, dispositions, decisions, dataset_sha=SHA, split_sha=SHA,
                          retrieval_sha=SHA, feature_schema_sha=SHA, model_sha=SHA, code_commit=COMMIT)


def test_evidence_signals_undefined_values_and_fingerprint_propagation():
    candidates = (candidate("a", "t", 2), candidate("a", "u", 3), candidate("r", "t"), candidate("r", "u"))
    scores = (score("a", "t", .9), score("a", "u", .8), score("r", "t", .5), score("r", "u", .4))
    ownership = global_ownership(scores)
    dispositions, decisions = decode(ownership, ("empty", "r", "a"))
    capsules = evidence_capsules(candidates, scores, ownership, dispositions, decisions, dataset_sha=SHA, split_sha=SHA,
                                retrieval_sha=SHA, feature_schema_sha=SHA, model_sha=SHA, code_commit=COMMIT)
    by_id = {c.s1_id: c for c in capsules}
    a = by_id["a"]
    assert a.candidate_count == 2 and a.top_candidate_score == .9
    assert a.min_accepted_lane_count == 2 and a.all_accepted_have_alternate_lane is True
    assert a.min_ownership_margin == pytest.approx(.4)
    assert a.min_threshold_margin == pytest.approx(.16)
    assert a.ambiguity_ratio == pytest.approx(.8 / .9)
    assert a.dataset_fingerprint == a.split_fingerprint == a.model_sha256 == SHA
    for query in ("empty", "r"):
        row = by_id[query]
        assert row.accepted_targets == ()
        assert row.min_ownership_margin is row.min_accepted_lane_count is row.min_threshold_margin is None
    assert by_id["empty"].top_candidate_score is None
    assert by_id["r"].top_candidate_score == .5
    with pytest.raises(ValueError, match="undefined"):
        replace(by_id["empty"], min_threshold_margin=0.)


def test_calibration_hand_computed_bins_and_undefined_domains():
    report = calibration_report((0, 1, 0, 1), (0., 1., .25, .75), "P0/calibration", bins=2)
    assert report["auroc"] == report["auprc"] == 1.
    assert report["brier_score"] == .03125
    assert report["ece"] == .125
    assert sum(b["count"] for b in report["bins"]) == 4
    assert report["bins"][0]["mean_score"] == .125
    assert report["calibration_slope"] is None
    for labels, values in (((), ()), ((0, 0), (.2, .3)), ((1, 1), (.2, .3))):
        result = calibration_report(labels, values, "P0/tiny")
        assert result["auroc"] is result["auprc"] is None
    with pytest.raises(ValueError):
        calibration_report((1,), (.4, .5), "P0/bad")
