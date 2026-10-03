"""Measured cohorts, compact Failure Atlas and raw confidence/structure diagnostics."""

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass

import pyarrow as pa

from concord.c3_contracts import STAGES
from concord.contracts import require_id
from concord.evaluation.quality import quality_report
from concord.features.reference import dominant_script
from concord.inference.resolution import keyed
from concord.metadata import canonical_json, require_sha256


def cohort_members(records, truth, candidates, scores, ownership):
    queries = [r for r in records if r.source == "S1"]
    targets = {r.entity_id: r for r in records if r.source != "S1"}
    truths = defaultdict(list)
    for q, t in truth:
        truths[q].append(t)
    counts = Counter(c.target_id for c in candidates)
    result = defaultdict(list)
    sm = defaultdict(list)
    for row in scores:
        sm[row.s1_id].append(row.score)
    om = defaultdict(list)
    for row in ownership:
        if row.is_owner and row.score >= .640 and row.rival_margin is not None:
            om[row.s1_id].append(row.rival_margin)
    for q in queries:
        script = dominant_script(q.business_name or "")
        cross = any(script != dominant_script(targets[t].business_name or "") and
                    "UNKNOWN" not in (script, dominant_script(targets[t].business_name or "")) for t in truths[q.entity_id])
        tags = ["cross_script" if cross else "same_script_or_no_truth", "country:" + (q.country or "None"),
                "name_present" if q.business_name else "name_missing_or_empty",
                "address_present" if q.business_address else "address_missing_or_empty",
                "truth_zero" if not truths[q.entity_id] else "truth_single" if len(truths[q.entity_id]) == 1 else "truth_multi"]
        competition = max((counts[c.target_id] for c in candidates if c.s1_id == q.entity_id), default=0)
        tags.append("competition_gt8" if competition > 8 else "competition_le8")
        query_candidates = [c for c in candidates if c.s1_id == q.entity_id]
        for lane in ("name", "compact", "address", "combined", "reverse"):
            if any(e.lane == lane for c in query_candidates for e in c.lane_evidence):
                tags.append("retrieved_by:" + lane)
        minimum = min(om[q.entity_id], default=None)
        tags.append("ownership_margin_undefined" if minimum is None else "ownership_margin_le001" if minimum <= .01 else "ownership_margin_gt001")
        for tag in tags:
            result[tag].append(q.entity_id)
    return {tag: tuple(sorted(ids)) for tag, ids in sorted(result.items())}


def cohorts(records, truth, candidates, scores, ownership, decisions, population):
    result = {}
    for tag, ids in cohort_members(records, truth, candidates, scores, ownership).items():
        subset = set(ids)
        report = quality_report(ids, tuple(p for p in truth if p[0] in subset),
                                tuple(d for d in decisions if d.s1_id in subset), population + "/" + tag)
        result[tag] = {k: report[k] for k in ("query_count", "macro_f05", "macro_precision", "macro_recall", "exact_set_accuracy", "tp", "fp", "fn")}
    return result


@dataclass(frozen=True, slots=True)
class FailureAtlasEntry:
    s1_id: str
    target_id: str
    error_type: str
    failure_stage: str
    source_json: str
    truth_targets: tuple[str, ...]
    accepted_targets: tuple[str, ...]
    candidate_count: int
    candidate_evidence_json: str
    run_identity_sha256: str

    def __post_init__(self):
        require_id(self.s1_id)
        require_id(self.target_id)
        if self.error_type not in ("FALSE_NEGATIVE", "FALSE_POSITIVE") or self.failure_stage not in STAGES:
            raise ValueError("C3 error/stage required")
        for values in (self.truth_targets, self.accepted_targets):
            if type(values) is not tuple or values != tuple(sorted(set(values))):
                raise ValueError("atlas sets must be immutable, sorted and unique")
        if type(self.candidate_count) is not int or self.candidate_count < 0:
            raise ValueError("nonnegative candidate count required")
        require_sha256(self.run_identity_sha256)


ATLAS_SCHEMA = pa.schema([
    pa.field(n, t, False) for n, t in (
        ("s1_id", pa.string()), ("target_id", pa.string()), ("error_type", pa.string()),
        ("failure_stage", pa.string()), ("source_json", pa.string()),
        ("truth_targets", pa.list_(pa.field("element", pa.string(), False))),
        ("accepted_targets", pa.list_(pa.field("element", pa.string(), False))),
        ("candidate_count", pa.int32()), ("candidate_evidence_json", pa.string()),
        ("run_identity_sha256", pa.string()))], metadata={b"concord.schema_version": b"concord.c4.failure-atlas.v1"})


def atlas(records, truth, candidates, scores, ownership, dispositions, decisions, failures, identity):
    cm, sm, om, dm = (keyed(rows) for rows in (candidates, scores, ownership, dispositions))
    if not (cm.keys() == sm.keys() == om.keys() == dm.keys()):
        raise ValueError("atlas requires complete aligned pipeline artifacts")
    sources = {r.entity_id: r for r in records if r.source == "S1"}
    targets = {r.entity_id: r for r in records if r.source != "S1"}
    truth_sets = defaultdict(set)
    for q, t in truth:
        truth_sets[q].add(t)
    sets = {d.s1_id: d.accepted_targets for d in decisions}
    rows = []
    for f in failures:
        relevant = sorted((k for k in cm if k[0] == f.s1_id), key=lambda k: (-sm[k].score, k[1]))
        # Keep top eight plus the attributed pair if retrieved; explicitly bounded.
        chosen = relevant[:8]
        key = f.s1_id, f.target_id
        if key in cm and key not in chosen:
            chosen.append(key)
        evidence = [{"target": asdict(targets[k[1]]), "retrieval": asdict(cm[k]), "score": asdict(sm[k]),
                     "ownership": asdict(om[k]), "disposition": asdict(dm[k])} for k in chosen]
        rows.append(FailureAtlasEntry(f.s1_id, f.target_id, f.error_type, f.failure_stage,
            canonical_json(asdict(sources[f.s1_id])).decode(), tuple(sorted(truth_sets[f.s1_id])), sets[f.s1_id],
            len(relevant), canonical_json(evidence).decode(), identity))
    return tuple(rows)


def structure_inputs(capsules, dispositions):
    ids, confidence, structure, raw = [], [], [], []
    for c in capsules:
        selected = [d for d in dispositions if d.s1_id == c.s1_id]
        accepted = [d.score for d in selected if d.accepted]
        rejected = [d.score for d in selected if not d.accepted]
        ordered = sorted((d.score for d in selected), reverse=True)
        # Predeclared zero-match confidence: no high-scoring rejected candidate.
        confidence.append(1 - min(accepted) if accepted else (c.top_candidate_score or 0.))
        structure.append(float(np_mean((
            1 - (c.min_accepted_lane_count or 0) / 5,
            1 - min(1., c.min_ownership_margin or 0.),
            1 - min(1., (c.min_threshold_margin or 0.) / .36), c.ambiguity_ratio or 0.))))
        ids.append(c.s1_id)
        raw.append({"s1_id": c.s1_id, "top_candidate_score": c.top_candidate_score,
                    "minimum_accepted_score": min(accepted) if accepted else None,
                    "best_rejected_score": max(rejected) if rejected else None,
                    "score_gap": ordered[0] - ordered[1] if len(ordered) > 1 else None})
    return tuple(ids), confidence, structure, raw


def np_mean(values):
    return sum(values) / len(values)
