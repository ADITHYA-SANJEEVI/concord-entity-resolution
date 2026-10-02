# Proposed Data Contract v1.1 — Concord Core Types

**Status:** AUTHORITATIVE TARGET CONTRACT FOR NEW CONCORD  
**Historical legacy code:** unchanged

---

## 1. Rules

- Missing is `None`.
- Empty is `""`.
- IDs are opaque non-empty strings.
- `source` is explicit; it is never inferred from `entity_id`.
- `country` is an optional opaque dataset label.
- Raw and normalized values are both preserved.
- Base normalization does not transliterate, strip punctuation, collapse whitespace, remove suffixes, or expand addresses.
- Public object contracts are immutable.
- Mutable NumPy/PyArrow representations are allowed only inside batch-processing implementations.

---

## 2. Core types

```python
from dataclasses import dataclass
from typing import Literal

Source = Literal["S1", "S2", "S3"]
RetrievalLane = Literal["name", "compact", "address", "combined", "reverse"]

@dataclass(frozen=True, slots=True)
class EntityRecord:
    entity_id: str
    source: Source
    business_name: str | None
    business_address: str | None
    country: str | None
    schema_version: str = "concord.entity.v1"


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
```

Validation:

- `entity_id.strip()` must be non-empty.
- `source` must be S1/S2/S3.
- no ID prefix contract exists.
- empty strings are allowed and preserved.
- `None` is allowed and preserved.
- normalization of `None` returns `None`.
- normalization of `""` returns `""`.

---

## 3. Retrieval view materialization

Retrieval-specific representations are C2 objects, not fields on `NormalizedEntity`.

```python
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
    view_version: str
```

At this boundary only:

- `None` may be converted to `""` for vectorizer input;
- missingness remains separately recorded.

---

## 4. Lane provenance

No mutable dictionaries and no `999` sentinel.

```python
@dataclass(frozen=True, slots=True)
class LaneEvidence:
    lane: RetrievalLane
    rank: int
    similarity: float

@dataclass(frozen=True, slots=True)
class RetrievalCandidate:
    s1_id: str
    target_id: str
    target_source: Literal["S2", "S3"]
    country: str | None
    retrieval_view_mask: int
    lane_evidence: tuple[LaneEvidence, ...]
```

Rules:

- rank is 1-based within a lane;
- absence from a lane means no `LaneEvidence` entry;
- mask and lane entries must validate against each other;
- duplicate `(s1_id, target_id)` candidates are forbidden after union.

---

## 5. Features

```python
@dataclass(frozen=True, slots=True)
class FeatureRow:
    s1_id: str
    target_id: str
    values: tuple[float, ...]
    schema_version: str
    schema_sha256: str
```

For the historical reference schema:

- exactly 59 values;
- cast to float32 at the batch/model boundary;
- ordered schema identity is authoritative.

The tuple is immutable; NumPy arrays may be created internally for vectorized execution.

---

## 6. Scoring

```python
@dataclass(frozen=True, slots=True)
class ScoredCandidate:
    s1_id: str
    target_id: str
    target_source: Literal["S2", "S3"]
    score: float
    model_sha256: str
    model_version: str
```

It contains **no** ownership or decoder fields.

---

## 7. Ownership

```python
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
    ownership_policy_version: str
```

For the historical reference policy:

- order target competitors by `score DESC, s1_id ASC`;
- exactly one rank-1 owner exists per target candidate set.

---

## 8. Candidate disposition / decoder

```python
@dataclass(frozen=True, slots=True)
class CandidateDisposition:
    s1_id: str
    target_id: str
    score: float
    is_owner: bool
    threshold: float
    threshold_margin: float
    accepted: bool
    rejection_reason: Literal[
        "NONE",
        "BELOW_THRESHOLD",
        "LOST_OWNERSHIP",
        "SET_POLICY"
    ]
    decoder_version: str
```

Historical baseline acceptance:

`accepted = is_owner and score >= 0.640`

---

## 9. Resolution decision

```python
@dataclass(frozen=True, slots=True)
class ResolutionDecision:
    s1_id: str
    accepted_targets: tuple[str, ...]
    decision_type: Literal["zero_match", "single_match", "multi_match"]
    decoder_version: str
```

Rejected candidates remain available in candidate-disposition artifacts rather than bloating every resolution object.

---

## 10. Failure attribution

```python
@dataclass(frozen=True, slots=True)
class FailureAttribution:
    s1_id: str
    target_id: str
    error_type: Literal["FALSE_NEGATIVE", "FALSE_POSITIVE"]
    failure_stage: Literal[
        "RETRIEVAL",
        "SCORING",
        "OWNERSHIP",
        "DECODING",
        "AMBIGUOUS_OR_INSUFFICIENT_EVIDENCE"
    ]
    tags: tuple[str, ...]
    diagnostics: tuple[tuple[str, str | float | int | bool | None], ...]
    attribution_policy_version: str
```

Attribution means "policy stage where the labelled outcome becomes unreachable", not causal proof.

False-negative precedence:

1. not retrieved -> RETRIEVAL
2. retrieved but score below admissibility threshold -> SCORING
3. score admissible but loses ownership -> OWNERSHIP
4. score admissible + owns target but set policy excludes -> DECODING
5. only genuine label/data ambiguity -> AMBIGUOUS

---

## 11. Resolution evidence capsule

```python
@dataclass(frozen=True, slots=True)
class ResolutionEvidenceRecord:
    s1_id: str
    decision_type: Literal["zero_match", "single_match", "multi_match"]
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
```

There is deliberately no `is_stable` field.

---

## 12. Fingerprint contracts

### Dataset

Canonical identity:

- sort by `(source, entity_id)`;
- reject duplicates;
- include entity schema version;
- encode every field with typed canonical JSON;
- preserve `null` distinct from `""`;
- SHA-256 the canonical UTF-8 stream.

Physical Parquet row order does not affect the digest.

### Split

Canonical identity includes:

- split schema version;
- dataset fingerprint;
- split purpose/name;
- sorted member identities.

---

## 13. Parquet schemas

Canonical internal tables:

- `entities.parquet`
- `normalized_entities.parquet`
- `retrieval_candidates.parquet`
- `features.parquet`
- `scores.parquet`
- `ownership.parquet`
- `candidate_dispositions.parquet`
- `resolutions.parquet`
- `failure_attribution.parquet`

Prefer flat typed columns for high-volume artifacts.

Nested evidence capsules may be JSON because they are diagnostic metadata, not the hot-path batch representation.

---

## 14. Invariants

1. raw records are never mutated;
2. normalization version is explicit;
3. candidate keys are unique after union;
4. retrieval mask and lane evidence agree;
5. feature schema/order/hash agree;
6. probabilities are finite and in `[0,1]`;
7. every target has at most one owner;
8. every accepted target is owned;
9. every accepted target satisfies the active decoder policy;
10. zero-match is an empty tuple, not a null set;
11. undefined diagnostic numbers use `None`;
12. all content identities are platform-independent.
