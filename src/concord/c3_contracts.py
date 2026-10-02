"""Immutable stage boundaries for C3; stages never acquire downstream fields."""

from dataclasses import dataclass
from math import isfinite
from typing import Literal

from concord.contracts import require_id
from concord.metadata import require_sha256

FEATURE_VERSION = "concord.features.historical-59.v1"
MODEL_VERSION = "concord.lightgbm.reference.v1"
OWNERSHIP_VERSION = "concord.ownership.score-desc-id-asc.v1"
DECODER_VERSION = "concord.decoder.historical-0640.v1"
ATTRIBUTION_VERSION = "concord.attribution.earliest-policy-stage.v1"
DecisionType = Literal["zero_match", "single_match", "multi_match"]
FailureStage = Literal["RETRIEVAL", "SCORING", "OWNERSHIP", "DECODING",
                       "AMBIGUOUS_OR_INSUFFICIENT_EVIDENCE"]
STAGES = ("RETRIEVAL", "SCORING", "OWNERSHIP", "DECODING",
          "AMBIGUOUS_OR_INSUFFICIENT_EVIDENCE")


def finite(value: float) -> None:
    if type(value) not in (int, float) or not isfinite(value):
        raise ValueError("numeric values must be finite")


def probability(value: float) -> None:
    finite(value)
    if not 0 <= value <= 1:
        raise ValueError("probability must be in [0,1]")


def pair(s1_id: str, target_id: str) -> None:
    require_id(s1_id)
    require_id(target_id)


def boolean(value: bool) -> None:
    if type(value) is not bool:
        raise ValueError("expected bool")


def decision(s1_id: str, targets: tuple[str, ...], kind: str) -> None:
    require_id(s1_id)
    if type(targets) is not tuple:
        raise ValueError("accepted targets must be an immutable tuple")
    for target in targets:
        require_id(target)
    if targets != tuple(sorted(set(targets))):
        raise ValueError("accepted targets must be sorted and unique")
    expected = "zero_match" if not targets else "single_match" if len(targets) == 1 else "multi_match"
    if kind != expected:
        raise ValueError("decision type disagrees with accepted set")


@dataclass(frozen=True, slots=True)
class FeatureRow:
    s1_id: str
    target_id: str
    values: tuple[float, ...]
    schema_version: str
    schema_sha256: str

    def __post_init__(self) -> None:
        pair(self.s1_id, self.target_id)
        if type(self.values) is not tuple or len(self.values) != 59:
            raise ValueError("historical reference requires 59 immutable ordered values")
        for value in self.values:
            finite(value)
        if self.schema_version != FEATURE_VERSION:
            raise ValueError("unsupported feature version")
        require_sha256(self.schema_sha256)


@dataclass(frozen=True, slots=True)
class ScoredCandidate:
    s1_id: str
    target_id: str
    target_source: Literal["S2", "S3"]
    score: float
    model_sha256: str
    model_version: str = MODEL_VERSION

    def __post_init__(self) -> None:
        pair(self.s1_id, self.target_id)
        if self.target_source not in ("S2", "S3"):
            raise ValueError("explicit target source S2/S3 required")
        probability(self.score)
        require_sha256(self.model_sha256)
        if not isinstance(self.model_version, str) or not self.model_version.strip():
            raise ValueError("explicit scorer model version required")


@dataclass(frozen=True, slots=True)
class OwnershipResult:
    s1_id: str
    target_id: str
    score: float
    is_owner: bool
    owner_rank: int
    rival_s1_id: str | None
    rival_score: float | None
    rival_margin: float | None
    ownership_policy_version: str = OWNERSHIP_VERSION

    def __post_init__(self) -> None:
        pair(self.s1_id, self.target_id)
        probability(self.score)
        boolean(self.is_owner)
        if type(self.owner_rank) is not int or self.owner_rank < 1:
            raise ValueError("owner rank must be positive")
        if self.is_owner != (self.owner_rank == 1):
            raise ValueError("rank 1 alone is owner")
        rival = (self.rival_s1_id, self.rival_score, self.rival_margin)
        if any(v is None for v in rival) and not all(v is None for v in rival):
            raise ValueError("rival diagnostics must be defined together")
        if self.rival_s1_id is not None:
            require_id(self.rival_s1_id)
            if self.rival_s1_id == self.s1_id:
                raise ValueError("cannot rival self")
            probability(self.rival_score)
            finite(self.rival_margin)
            if abs(self.rival_margin - (self.score - self.rival_score)) > 1e-12:
                raise ValueError("rival margin disagrees with scores")
            if (self.is_owner and self.rival_margin < 0
                    or not self.is_owner and self.rival_margin > 0):
                raise ValueError("rival scores disagree with owner order")
        elif not self.is_owner:
            raise ValueError("a loser must have a rival")
        if self.ownership_policy_version != OWNERSHIP_VERSION:
            raise ValueError("unsupported ownership policy")


@dataclass(frozen=True, slots=True)
class CandidateDisposition:
    s1_id: str
    target_id: str
    score: float
    is_owner: bool
    threshold: float
    threshold_margin: float
    accepted: bool
    rejection_reason: Literal["NONE", "BELOW_THRESHOLD", "LOST_OWNERSHIP", "SET_POLICY"]
    decoder_version: str = DECODER_VERSION

    def __post_init__(self) -> None:
        pair(self.s1_id, self.target_id)
        probability(self.score)
        boolean(self.is_owner)
        boolean(self.accepted)
        if self.threshold != .640 or self.decoder_version != DECODER_VERSION:
            raise ValueError("historical decoder is frozen at 0.640")
        finite(self.threshold_margin)
        if abs(self.threshold_margin - (self.score - self.threshold)) > 1e-12:
            raise ValueError("threshold margin mismatch")
        expected = self.is_owner and self.score >= self.threshold
        reason = "NONE" if expected else "BELOW_THRESHOLD" if self.score < self.threshold else "LOST_OWNERSHIP"
        if self.accepted != expected or self.rejection_reason != reason:
            raise ValueError("disposition violates historical acceptance/rejection policy")


@dataclass(frozen=True, slots=True)
class ResolutionDecision:
    s1_id: str
    accepted_targets: tuple[str, ...]
    decision_type: DecisionType
    decoder_version: str = DECODER_VERSION

    def __post_init__(self) -> None:
        decision(self.s1_id, self.accepted_targets, self.decision_type)
        if self.decoder_version != DECODER_VERSION:
            raise ValueError("unsupported decoder")


@dataclass(frozen=True, slots=True)
class FailureAttribution:
    s1_id: str
    target_id: str
    error_type: Literal["FALSE_NEGATIVE", "FALSE_POSITIVE"]
    failure_stage: FailureStage
    tags: tuple[str, ...]
    diagnostics: tuple[tuple[str, str | float | int | bool | None], ...]
    attribution_policy_version: str = ATTRIBUTION_VERSION

    def __post_init__(self) -> None:
        pair(self.s1_id, self.target_id)
        if self.error_type not in ("FALSE_NEGATIVE", "FALSE_POSITIVE") or self.failure_stage not in STAGES:
            raise ValueError("unknown error/stage")
        if (type(self.tags) is not tuple or any(type(t) is not str for t in self.tags)
                or self.tags != tuple(sorted(set(self.tags)))):
            raise ValueError("tags must be immutable, sorted, unique strings")
        if type(self.diagnostics) is not tuple:
            raise ValueError("diagnostics must be immutable")
        keys = []
        for item in self.diagnostics:
            if type(item) is not tuple or len(item) != 2 or not isinstance(item[0], str):
                raise ValueError("diagnostics require fixed scalar pairs")
            keys.append(item[0])
            value = item[1]
            if value is not None and type(value) not in (str, bool, float, int):
                raise ValueError("diagnostics require scalar values")
            if type(value) in (float, int):
                finite(value)
        if len(keys) != len(set(keys)) or self.attribution_policy_version != ATTRIBUTION_VERSION:
            raise ValueError("invalid diagnostic keys/policy")


@dataclass(frozen=True, slots=True)
class ResolutionEvidenceRecord:
    s1_id: str
    decision_type: DecisionType
    accepted_targets: tuple[str, ...]
    candidate_count: int
    top_candidate_score: float | None
    min_accepted_lane_count: int | None
    all_accepted_have_alternate_lane: bool | None
    min_ownership_margin: float | None
    min_threshold_margin: float | None
    ambiguity_ratio: float | None
    dataset_fingerprint: str
    split_fingerprint: str | None
    retrieval_config_sha256: str
    feature_schema_sha256: str
    model_sha256: str
    decoder_config_sha256: str
    code_commit: str

    def __post_init__(self) -> None:
        decision(self.s1_id, self.accepted_targets, self.decision_type)
        if type(self.candidate_count) is not int or self.candidate_count < len(self.accepted_targets):
            raise ValueError("invalid candidate count")
        for value in (self.top_candidate_score, self.ambiguity_ratio):
            if value is not None:
                probability(value)
        for value in (self.min_ownership_margin, self.min_threshold_margin):
            if value is not None:
                finite(value)
                if value < 0:
                    raise ValueError("accepted margins must be nonnegative")
        if self.min_accepted_lane_count is not None and (
                type(self.min_accepted_lane_count) is not int or not 1 <= self.min_accepted_lane_count <= 5):
            raise ValueError("invalid accepted lane count")
        if self.all_accepted_have_alternate_lane is not None:
            boolean(self.all_accepted_have_alternate_lane)
        if self.accepted_targets and any(v is None for v in (
                self.min_accepted_lane_count, self.all_accepted_have_alternate_lane, self.min_threshold_margin)):
            raise ValueError("nonempty decisions require accepted lane/threshold diagnostics")
        if (self.min_accepted_lane_count is not None
                and self.all_accepted_have_alternate_lane != (self.min_accepted_lane_count >= 2)):
            raise ValueError("alternate-lane diagnostic disagrees with lane count")
        if self.candidate_count < 2 and self.ambiguity_ratio is not None:
            raise ValueError("ambiguity ratio requires two candidates")
        if not self.accepted_targets and any(v is not None for v in (
                self.min_accepted_lane_count, self.all_accepted_have_alternate_lane,
                self.min_ownership_margin, self.min_threshold_margin)):
            raise ValueError("zero-match accepted diagnostics are undefined")
        if (self.top_candidate_score is None) != (self.candidate_count == 0):
            raise ValueError("top score requires candidates")
        for value in (self.dataset_fingerprint, self.retrieval_config_sha256,
                      self.feature_schema_sha256, self.model_sha256, self.decoder_config_sha256):
            require_sha256(value)
        if self.split_fingerprint is not None:
            require_sha256(self.split_fingerprint)
        if len(self.code_commit) != 40 or any(c not in "0123456789abcdef" for c in self.code_commit):
            raise ValueError("full Git commit required")
