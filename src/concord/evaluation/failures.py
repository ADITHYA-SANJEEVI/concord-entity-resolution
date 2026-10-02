"""Earliest policy-gate attribution, not causal proof or C4 Failure Atlas research."""

from collections import Counter
from dataclasses import asdict

from concord.c3_contracts import STAGES, FailureAttribution, probability
from concord.inference.resolution import keyed


def attribute_stage(*, error_type: str, retrieved: bool, score: float | None,
                    is_owner: bool | None, emitted: bool, ambiguity_reason: str | None = None) -> str:
    if error_type not in ("FALSE_NEGATIVE", "FALSE_POSITIVE"):
        raise ValueError("unknown error type")
    if ambiguity_reason is not None:
        if not isinstance(ambiguity_reason, str) or not ambiguity_reason.strip():
            raise ValueError("explicit genuine label/data ambiguity reason required")
        return "AMBIGUOUS_OR_INSUFFICIENT_EVIDENCE"
    if score is not None:
        probability(score)
    if error_type == "FALSE_POSITIVE":
        if not emitted:
            raise ValueError("false positive must be emitted")
        return "SCORING" if retrieved and score is not None and score >= .640 else "DECODING"
    if emitted:
        raise ValueError("false negative cannot be emitted")
    if not retrieved:
        return "RETRIEVAL"
    if score is None or type(is_owner) is not bool:
        raise ValueError("incomplete pipeline is not genuine label ambiguity")
    if score < .640:
        return "SCORING"
    return "OWNERSHIP" if not is_owner else "DECODING"


def attribute_failures(query_ids, truth, candidates, scores, ownership, dispositions, decisions,
                       ambiguities: tuple[tuple[str, str, str], ...] = ()) -> tuple[FailureAttribution, ...]:
    cm, sm, om, dm = (keyed(rows) for rows in (candidates, scores, ownership, dispositions))
    if not (cm.keys() == sm.keys() == om.keys() == dm.keys()):
        raise ValueError("complete pipeline evidence required for attribution")
    if any(sm[k].score != om[k].score or sm[k].score != dm[k].score or om[k].is_owner != dm[k].is_owner for k in cm):
        raise ValueError("inconsistent stage evidence")
    if len(set(truth)) != len(truth) or any(q not in query_ids for q, _ in truth):
        raise ValueError("invalid evaluation truth")
    if {d.s1_id for d in decisions} != set(query_ids) or len(decisions) != len(query_ids):
        raise ValueError("resolution population mismatch")
    ambiguous = {(q, t): reason for q, t, reason in ambiguities}
    if len(ambiguous) != len(ambiguities) or any(q not in query_ids for q, _ in ambiguous):
        raise ValueError("invalid explicit ambiguity annotations")
    predictions = {(d.s1_id, t) for d in decisions for t in d.accepted_targets}
    truths, result = set(truth), []
    for error_type, pairs in (("FALSE_NEGATIVE", truths - predictions), ("FALSE_POSITIVE", predictions - truths)):
        for key in sorted(pairs):
            c, s, o, d = cm.get(key), sm.get(key), om.get(key), dm.get(key)
            reason = ambiguous.get(key)
            stage = attribute_stage(error_type=error_type, retrieved=c is not None,
                                    score=s.score if s else None, is_owner=o.is_owner if o else None,
                                    emitted=key in predictions, ambiguity_reason=reason)
            truth_count = sum(q == key[0] for q, _ in truth)
            tags = ["ZERO_MATCH"] if not truth_count else ["MULTI_MATCH"] if truth_count > 1 else []
            if c and c.contributing_lane_count == 1:
                tags.append("SINGLE_LANE")
            diagnostics = (("retrieved", c is not None), ("score", s.score if s else None),
                           ("is_owner", o.is_owner if o else None), ("rival_s1_id", o.rival_s1_id if o else None),
                           ("rival_margin", o.rival_margin if o else None),
                           ("rejection_reason", d.rejection_reason if d else None),
                           ("label_ambiguity_reason", reason))
            result.append(FailureAttribution(*key, error_type, stage, tuple(sorted(tags)), diagnostics))
    return tuple(sorted(result, key=lambda r: (r.s1_id, r.target_id, r.error_type)))


def failure_report(rows: tuple[FailureAttribution, ...], population: str) -> dict:
    return {"schema_version": "concord.failure-attribution.v1", "population": population,
            "meaning": "Earliest policy stage, not causal proof",
            "counts": {kind: {stage: sum(r.error_type == kind and r.failure_stage == stage for r in rows)
                               for stage in STAGES} for kind in ("FALSE_NEGATIVE", "FALSE_POSITIVE")},
            "tag_counts": dict(sorted(Counter(tag for r in rows for tag in r.tags).items())),
            "examples": [asdict(row) for row in rows[:12]]}
