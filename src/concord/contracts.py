"""Immutable C1/C2 contracts. Later pipeline stages deliberately remain unimplemented."""

from dataclasses import dataclass
from math import isfinite
from typing import Literal

Source = Literal["S1", "S2", "S3"]
RetrievalLane = Literal["name", "compact", "address", "combined", "reverse"]
LANES: tuple[RetrievalLane, ...] = ("name", "compact", "address", "combined", "reverse")
ENTITY_VERSION = "concord.entity.v1"
VIEWS_VERSION = "concord.retrieval-text.reference.v1"


def require_id(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("entity IDs must be non-empty opaque strings")


def optional_text(value: str | None) -> None:
    if value is not None and not isinstance(value, str):
        raise ValueError("text must be a string or None; string sentinels are never coerced")


@dataclass(frozen=True, slots=True)
class EntityRecord:
    entity_id: str
    source: Source
    business_name: str | None
    business_address: str | None
    country: str | None = None
    schema_version: str = ENTITY_VERSION

    def __post_init__(self) -> None:
        require_id(self.entity_id)
        if self.source not in ("S1", "S2", "S3"):
            raise ValueError("source must be explicit S1/S2/S3")
        for value in (self.business_name, self.business_address, self.country):
            optional_text(value)
        if self.schema_version != ENTITY_VERSION:
            raise ValueError("unsupported entity schema")


@dataclass(frozen=True, slots=True)
class NormalizedEntity:
    entity_id: str
    source: Source
    business_name_raw: str | None
    business_address_raw: str | None
    business_name_normalized: str | None
    business_address_normalized: str | None
    country: str | None
    normalization_version: str

    def __post_init__(self) -> None:
        from concord.normalization import NORMALIZATION_VERSION, normalize_text

        EntityRecord(self.entity_id, self.source, self.business_name_raw,
                     self.business_address_raw, self.country)
        if self.normalization_version != NORMALIZATION_VERSION:
            raise ValueError("unsupported normalization version / Unicode database")
        if (self.business_name_normalized != normalize_text(self.business_name_raw)
                or self.business_address_normalized != normalize_text(self.business_address_raw)):
            raise ValueError("normalized text must match the declared normalization")


@dataclass(frozen=True, slots=True)
class RetrievalTextViews:
    entity_id: str
    name: str
    compact: str
    address: str
    combined_name: str
    combined_address: str
    name_missing: bool
    address_missing: bool
    view_version: str = VIEWS_VERSION

    def __post_init__(self) -> None:
        require_id(self.entity_id)
        for value in (self.name, self.compact, self.address,
                      self.combined_name, self.combined_address):
            if not isinstance(value, str):
                raise ValueError("retrieval inputs must be strings")
        if type(self.name_missing) is not bool or type(self.address_missing) is not bool:
            raise ValueError("missingness flags must be bools")
        if self.view_version != VIEWS_VERSION:
            raise ValueError("unsupported retrieval view version")


@dataclass(frozen=True, slots=True)
class LaneEvidence:
    lane: RetrievalLane
    rank: int
    similarity: float

    def __post_init__(self) -> None:
        if self.lane not in LANES:
            raise ValueError("unknown retrieval lane")
        if type(self.rank) is not int or self.rank < 1:
            raise ValueError("lane ranks are positive, one-based integers")
        if (type(self.similarity) not in (float, int) or not isfinite(self.similarity)
                or not 0 < self.similarity <= 1.000001):
            raise ValueError("lane similarity must be finite, positive, and at most one")


@dataclass(frozen=True, slots=True)
class RetrievalCandidate:
    s1_id: str
    target_id: str
    target_source: Literal["S2", "S3"]
    country: str | None
    retrieval_view_mask: int
    lane_evidence: tuple[LaneEvidence, ...]

    def __post_init__(self) -> None:
        require_id(self.s1_id)
        require_id(self.target_id)
        optional_text(self.country)
        if self.target_source not in ("S2", "S3"):
            raise ValueError("target source must be S2/S3")
        if (type(self.lane_evidence) is not tuple or not self.lane_evidence
                or any(not isinstance(e, LaneEvidence) for e in self.lane_evidence)):
            raise ValueError("lane evidence must be a non-empty immutable tuple")
        lanes = tuple(e.lane for e in self.lane_evidence)
        if len(set(lanes)) != len(lanes):
            raise ValueError("duplicate lane evidence")
        if lanes != tuple(lane for lane in LANES if lane in lanes):
            raise ValueError("lane evidence must follow the fixed lane order")
        mask = sum(1 << LANES.index(lane) for lane in lanes)
        if type(self.retrieval_view_mask) is not int or self.retrieval_view_mask != mask:
            raise ValueError("retrieval mask and evidence disagree")

    @property
    def contributing_lane_count(self) -> int:
        return len(self.lane_evidence)

    def available_without(self, lane: RetrievalLane) -> bool:
        return bool(self.retrieval_view_mask & ~(1 << LANES.index(lane)))
