"""Separate global arbitration, frozen threshold decoding, and compact evidence."""

from collections import defaultdict
from dataclasses import asdict, dataclass

from concord.c3_contracts import (
    DECODER_VERSION,
    CandidateDisposition,
    OwnershipResult,
    ResolutionDecision,
    ResolutionEvidenceRecord,
    ScoredCandidate,
)
from concord.contracts import require_id
from concord.metadata import content_sha256


def keyed(rows):
    result = {(r.s1_id, r.target_id): r for r in rows}
    if len(result) != len(rows):
        raise ValueError("duplicate stage pair")
    return result


@dataclass(frozen=True, slots=True)
class DecoderConfig:
    threshold: float = .640
    decoder_version: str = DECODER_VERSION
    ownership_policy: str = "score DESC, s1_id ASC; global target population"

    def __post_init__(self):
        if (self.threshold != .640 or self.decoder_version != DECODER_VERSION
                or self.ownership_policy != "score DESC, s1_id ASC; global target population"):
            raise ValueError("reference ownership/decoder policy is frozen")

    @property
    def sha256(self):
        return content_sha256(asdict(self))


def global_ownership(scores: tuple[ScoredCandidate, ...]) -> tuple[OwnershipResult, ...]:
    keyed(scores)
    if len({(s.model_sha256, s.model_version) for s in scores}) > 1:
        raise ValueError("ownership requires scores from one model")
    groups = defaultdict(list)
    for row in scores:
        groups[row.target_id].append(row)
    result = []
    for group in groups.values():
        if len({r.target_source for r in group}) != 1:
            raise ValueError("ambiguous target source")
        ordered = sorted(group, key=lambda s: (-s.score, s.s1_id))
        for index, row in enumerate(ordered):
            rival = (ordered[1] if index == 0 else ordered[0]) if len(ordered) > 1 else None
            result.append(OwnershipResult(row.s1_id, row.target_id, row.score, index == 0, index + 1,
                                          rival.s1_id if rival else None, rival.score if rival else None,
                                          row.score - rival.score if rival else None))
    return tuple(sorted(result, key=lambda r: (r.s1_id, r.target_id)))


def decode(ownership: tuple[OwnershipResult, ...], query_ids: tuple[str, ...],
           config: DecoderConfig | None = None) -> tuple[tuple[CandidateDisposition, ...], tuple[ResolutionDecision, ...]]:
    config = config or DecoderConfig()
    keyed(ownership)
    if type(query_ids) is not tuple or len(set(query_ids)) != len(query_ids):
        raise ValueError("explicit unique query population required")
    for query in query_ids:
        require_id(query)
    groups = defaultdict(list)
    for row in ownership:
        if row.s1_id not in query_ids:
            raise ValueError("ownership contains queries outside the population")
        groups[row.target_id].append(row)
    for group in groups.values():
        ordered = sorted(group, key=lambda r: (-r.score, r.s1_id))
        if any(r.owner_rank != i + 1 or r.is_owner != (i == 0) for i, r in enumerate(ordered)):
            raise ValueError("ownership violates global score/ID arbitration")
    dispositions, accepted = [], defaultdict(list)
    for row in sorted(ownership, key=lambda r: (r.s1_id, r.target_id)):
        accept = row.is_owner and row.score >= config.threshold
        reason = "NONE" if accept else "BELOW_THRESHOLD" if row.score < config.threshold else "LOST_OWNERSHIP"
        dispositions.append(CandidateDisposition(row.s1_id, row.target_id, row.score, row.is_owner,
                                                config.threshold, row.score - config.threshold, accept, reason))
        if accept:
            accepted[row.s1_id].append(row.target_id)
    decisions = []
    for query in sorted(query_ids):
        targets = tuple(sorted(accepted[query]))
        kind = "zero_match" if not targets else "single_match" if len(targets) == 1 else "multi_match"
        decisions.append(ResolutionDecision(query, targets, kind))
    return tuple(dispositions), tuple(decisions)


def evidence_capsules(candidates, scores, ownership, dispositions, decisions, *,
                      dataset_sha: str, split_sha: str | None, retrieval_sha: str,
                      feature_schema_sha: str, model_sha: str, code_commit: str,
                      config: DecoderConfig | None = None) -> tuple[ResolutionEvidenceRecord, ...]:
    config = config or DecoderConfig()
    cm, sm, om, dm = (keyed(rows) for rows in (candidates, scores, ownership, dispositions))
    if not (cm.keys() == sm.keys() == om.keys() == dm.keys()):
        raise ValueError("evidence stage populations must match")
    if any(sm[k].score != om[k].score or sm[k].score != dm[k].score
           or sm[k].model_sha256 != model_sha or om[k].is_owner != dm[k].is_owner for k in cm):
        raise ValueError("evidence stages disagree")
    query_ids = tuple(d.s1_id for d in decisions)
    expected_dispositions, expected_decisions = decode(tuple(ownership), query_ids, config)
    if keyed(expected_dispositions) != dm or tuple(sorted(decisions, key=lambda d: d.s1_id)) != expected_decisions:
        raise ValueError("evidence must reflect actual frozen decoder output")
    records = []
    for d in sorted(decisions, key=lambda d: d.s1_id):
        related = [s for s in scores if s.s1_id == d.s1_id]
        ordered = sorted((s.score for s in related), reverse=True)
        accepted = [(d.s1_id, target) for target in d.accepted_targets]
        lanes = [cm[k].contributing_lane_count for k in accepted]
        margins = [om[k].rival_margin for k in accepted]
        records.append(ResolutionEvidenceRecord(
            d.s1_id, d.decision_type, d.accepted_targets, len(related),
            ordered[0] if ordered else None, min(lanes) if lanes else None,
            all(count >= 2 for count in lanes) if lanes else None,
            min(margins) if margins and all(m is not None for m in margins) else None,
            min(dm[k].threshold_margin for k in accepted) if accepted else None,
            ordered[1] / ordered[0] if len(ordered) >= 2 and ordered[0] > 0 else None,
            dataset_sha, split_sha, retrieval_sha, feature_schema_sha, model_sha, config.sha256, code_commit))
    return tuple(records)
