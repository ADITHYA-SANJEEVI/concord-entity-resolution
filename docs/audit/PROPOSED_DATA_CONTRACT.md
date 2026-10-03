# Proposed Data Contracts: Concord Core Types

**Repository:** `concord-entity-resolution`  
**Status:** SUPERSEDED PROPOSAL. New Concord uses the authoritative
[v1.1 data contract](../../Concord_Architecture_v1_1_AstraStyle/docs/audit/PROPOSED_DATA_CONTRACT_V1_1.md)
and Architecture Amendment 001. The older examples below are historical design
context, not the current implemented contracts or claims of implemented behavior.

---

## 1. Design Principles

1. **Strict Typing:** All pipeline transitions pass through typed, frozen dataclasses or PyArrow/Parquet schema equivalents.
2. **Explicit Null & Empty Semantics:** Empty strings, missing addresses, and zero-match sets are represented explicitly without ambiguous string sentinels (e.g., `None` or empty frozensets, not `"nan"` or `"NULL"`).
3. **Immutability:** Internal data representations are frozen (`frozen=True`) to prevent side-effects during parallel processing.
4. **Dual Serialization:** Bulk tabular records stream via **Parquet** (snappy/zstd compression, strongly typed columns). Metadata, summaries, and configurations serialize via canonical **UTF-8 JSON**.

---

## 2. Core Entity & Normalization Contracts

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Optional, Sequence
import numpy as np
from numpy.typing import NDArray

@dataclass(frozen=True)
class EntityRecord:
    """Raw, unnormalized business record as ingested from source storage."""
    entity_id: str                          # Format: 'S1-xxxx', 'S2-xxxx', 'S3-xxxx'
    business_name: str                      # Raw business name string
    business_address: str                   # Raw business address string
    country: str                            # ISO country code or regional string ('US', 'India', 'France')
    source: Literal["S1", "S2", "S3"]      # Source collection identifier


@dataclass(frozen=True)
class NormalizedEntity:
    """Clean, deterministically normalized business record with lineage tracking."""
    entity_id: str
    source: Literal["S1", "S2", "S3"]
    country: str
    name_raw: str                           # Preserved original name
    address_raw: str                        # Preserved original address
    name_normalized: str                    # NFKD decomposed, combining-stripped, case-folded
    address_normalized: str                 # NFKD decomposed, combining-stripped, case-folded
    name_compact: str                       # Whitespace stripped from normalized name
    normalization_version: str              # E.g., 'nfkd-casefold-v1'
    has_empty_name: bool = field(init=False)
    has_empty_address: bool = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, 'has_empty_name', len(self.name_normalized.strip()) == 0)
        object.__setattr__(self, 'has_empty_address', len(self.address_normalized.strip()) == 0)
```

---

## 3. Retrieval & Candidate Graph Contracts

```python
@dataclass(frozen=True)
class RetrievalCandidate:
    """Candidate pair emitted by bounded multi-view retrieval with full provenance."""
    s1_id: str                              # Source-1 query entity ID
    target_id: str                          # Target entity ID (S2 or S3)
    country: str                            # Partition country
    source: Literal["S2", "S3"]             # Target source origin
    retrieval_view_mask: int                # Bitmask (1=name, 2=compact, 4=address, 8=combined, 16=reverse)
    lane_ranks: dict[str, int]              # Per-lane rank (0-indexed, 999 = absent from top-K)
    cosine_scores: dict[str, float]         # Cosine similarities captured during retrieval

    @property
    def contributing_lane_count(self) -> int:
        """Count of retrieval lanes that generated this candidate pair."""
        return bin(self.retrieval_view_mask).count('1')

    def survives_lane_removal(self, lane_bit: int) -> bool:
        """True if candidate was found by at least one other lane if lane_bit is dropped."""
        return (self.retrieval_view_mask & ~lane_bit) > 0
```

---

## 4. Feature & Scoring Contracts

```python
@dataclass(frozen=True)
class FeatureRow:
    """Typed pairwise feature vector bound to an authoritative schema."""
    s1_id: str
    target_id: str
    source: Literal["S2", "S3"]
    features: NDArray[np.float32]           # Exactly 59 float32 feature values
    schema_version: str                     # Frozen legacy ID: 'asmi-crossscript-reproduced-59-v1'; not the C3 schema
    schema_sha256: str                      # Hash of ordered feature schema definition


@dataclass(frozen=True)
class ScoredCandidate:
    """Candidate pair scored by the classifier, with competitive context."""
    s1_id: str
    target_id: str
    source: Literal["S2", "S3"]
    score: float                            # Continuous probability in [0.0, 1.0]
    retrieval_view_mask: int
    target_owner_rank: int                  # Rank of this S1 among all queries competing for target_id
    target_rival_margin: float              # score - runner_up_score for target_id
    threshold_margin: float                 # score - decision_threshold (e.g., score - 0.640)
```

---

## 5. Decision & Resolution Contracts

```python
@dataclass(frozen=True)
class ResolutionDecision:
    """Final entity resolution decision for a single Source-1 query entity."""
    s1_id: str
    accepted_targets: tuple[str, ...]       # Ordered by score DESC, target_id ASC
    rejected_targets: tuple[str, ...]       # Candidates that failed ownership or threshold
    decision_type: Literal["zero_match", "single_match", "multi_match"]
    max_score: Optional[float]              # Top accepted score (None if zero matches)
    decision_threshold: float = 0.640       # Applied threshold
```

---

## 6. Diagnostic & Error Attribution Contracts

```python
@dataclass(frozen=True)
class FailureAttribution:
    """Deterministic root-cause attribution for a missed truth link or false positive."""
    s1_id: str
    target_id: str
    error_type: Literal["FALSE_NEGATIVE", "FALSE_POSITIVE"]
    
    # Primary Failure Stage (Mutually Exclusive)
    primary_stage: Literal[
        "RETRIEVAL",                        # Never entered candidate graph in any lane
        "RANKING",                          # Retrived, but model probability too low
        "OWNERSHIP",                        # Scored above threshold, but lost ownership to competing S1
        "DECODING",                         # Owned, but fell below decision threshold
        "AMBIGUOUS_OR_INSUFFICIENT_EVIDENCE"# Ground truth conflict / indistinguishable text
    ]
    
    # Orthogonal Failure Tags (Multiple May Apply)
    tags: tuple[Literal[
        "CROSS_SCRIPT",                     # Query and target in different scripts
        "COUNTRY_OOD",                      # Test country unrepresented in training (e.g. France)
        "TRANSLITERATION_DEPENDENT",        # Match relies on phonetic transliteration
        "NORMALIZATION_SENSITIVE",          # Punctuation/whitespace/suffix mismatch
        "SINGLE_LANE",                      # Retrieved by only one sparse view (fragile)
        "ZERO_MATCH",                       # Query expected zero matches
        "MULTI_MATCH",                      # Complex 1-to-many entity
        "HIGH_AMBIGUITY"                    # Common generic brand or address
    ], ...]
    
    diagnostics: dict[str, str | float | int] # Contextual metrics (e.g., rival margin, missing lane)
```

---

## 7. Lightweight Resolution Evidence Record & Stability

```python
@dataclass(frozen=True)
class ResolutionEvidenceRecord:
    """Lightweight audit trail emitted per S1 resolution set for stability evaluation."""
    s1_id: str
    decision_type: Literal["zero_match", "single_match", "multi_match"]
    accepted_target_count: int
    top_model_confidence: float             # Maximum candidate probability
    
    # System Stability Indicators
    min_lane_count: int                     # Minimum retrieval lanes supporting any accepted target
    all_survive_single_lane_removal: bool   # True if no accepted link drops out on any 1-lane ablation
    min_ownership_margin: float             # Narrowest rival margin among accepted targets
    min_threshold_margin: float             # Narrowest score margin above threshold
    candidate_set_size: int                 # Total candidates considered for this S1
    is_stable: bool                         # Compound stability indicator
    
    # Lineage Fingerprints
    model_sha256: str
    schema_sha256: str
    dataset_fingerprint: str
```
