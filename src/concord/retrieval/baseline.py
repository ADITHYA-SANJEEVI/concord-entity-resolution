"""Bounded historical five-view retrieval with explicit new-contract adapters.

No labels enter retrieval. Sparse top-N is computed per country, in chunks.
Reverse K bounds incoming edges per target, not outgoing edges per S1.
"""

import time
from dataclasses import asdict, dataclass
from math import isfinite

import numpy as np
import psutil
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer
from sparse_dot_topn import sp_matmul_topn

from concord.contracts import (
    LANES,
    LaneEvidence,
    NormalizedEntity,
    RetrievalCandidate,
    RetrievalTextViews,
)
from concord.metadata import content_sha256, require_sha256
from concord.storage import canonical_candidates

HISTORICAL_K = (5, 5, 5, 10, 8)


@dataclass(frozen=True, slots=True)
class RetrievalConfig:
    profile: str = "historical-five-view-v1"
    budgets: tuple[int, ...] = HISTORICAL_K
    min_df: int = 2
    max_df: float = .05
    fit_cap: int = 3_000_000
    seed: int = 0
    chunk_size: int = 250_000
    threads: int = 1
    lanes: tuple[str, ...] = LANES

    def __post_init__(self) -> None:
        if self.profile not in ("historical-five-view-v1", "historical-budget-variant-v1",
                                "synthetic-five-view-v1"):
            raise ValueError("unknown baseline/configuration profile; challengers are separate")
        if (type(self.budgets) is not tuple or len(self.budgets) != len(LANES)
                or any(type(k) is not int or k < 1 for k in self.budgets)):
            raise ValueError("five positive immutable lane budgets are required")
        for value in (self.min_df, self.fit_cap, self.chunk_size, self.threads):
            if type(value) is not int or value < 1:
                raise ValueError("positive integer execution parameters required")
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        if type(self.max_df) is not float or not 0 < self.max_df <= 1:
            raise ValueError("max_df must be a fraction in (0,1]")
        if (type(self.lanes) is not tuple or not self.lanes
                or self.lanes != tuple(lane for lane in LANES if lane in self.lanes)):
            raise ValueError("lanes must be unique and in historical order")
        if self.profile != "synthetic-five-view-v1" and (
                self.min_df != 2 or self.max_df != .05 or self.fit_cap != 3_000_000
                or self.seed != 0):
            raise ValueError("historical vectorizer/sampling semantics are frozen")
        if self.profile == "historical-five-view-v1" and (
                self.budgets != HISTORICAL_K or self.lanes != LANES):
            raise ValueError("baseline budgets/lanes are frozen; name budget variants explicitly")

    @property
    def fingerprint(self) -> str:
        return content_sha256(asdict(self))


def synthetic_config(budgets: tuple[int, ...] = HISTORICAL_K,
                     lanes: tuple[str, ...] = LANES, **kwargs) -> RetrievalConfig:
    return RetrievalConfig(profile="synthetic-five-view-v1", min_df=1, max_df=1.0,
                           budgets=budgets, lanes=lanes, **kwargs)


@dataclass(frozen=True, slots=True)
class FitEvidence:
    country: str | None
    view: str
    sample_fingerprint: str
    sample_count: int
    vocabulary_size: int
    query_nnz: int
    target_nnz: int

    def __post_init__(self) -> None:
        if self.country is not None and not isinstance(self.country, str):
            raise ValueError("country must be an optional string")
        if self.view not in LANES[:3]:
            raise ValueError("fit evidence refers to a base vectorizer")
        require_sha256(self.sample_fingerprint)
        for count in (self.sample_count, self.vocabulary_size, self.query_nnz, self.target_nnz):
            if type(count) is not int or count < 0:
                raise ValueError("fit counts must be nonnegative integers")


@dataclass(frozen=True, slots=True)
class RetrievalRun:
    candidates: tuple[RetrievalCandidate, ...]
    config: RetrievalConfig
    fit_evidence: tuple[FitEvidence, ...]
    warnings: tuple[str, ...]
    wall_seconds: float
    cpu_seconds: float
    sampled_peak_rss_bytes: int
    peak_process_rss_bytes: int
    eligible_cartesian_pairs: int
    candidate_pair_bound: int

    def __post_init__(self) -> None:
        for values, kind in ((self.candidates, RetrievalCandidate), (self.fit_evidence, FitEvidence),
                             (self.warnings, str)):
            if type(values) is not tuple or any(not isinstance(v, kind) for v in values):
                raise ValueError("run containers must be immutable typed tuples")
        if not isinstance(self.config, RetrievalConfig):
            raise ValueError("run configuration must be immutable")
        for seconds in (self.wall_seconds, self.cpu_seconds):
            if type(seconds) not in (float, int) or not isfinite(seconds) or seconds < 0:
                raise ValueError("run timings must be finite and nonnegative")
        for count in (self.sampled_peak_rss_bytes, self.peak_process_rss_bytes,
                      self.eligible_cartesian_pairs, self.candidate_pair_bound):
            if type(count) is not int or count < 0:
                raise ValueError("run counts must be nonnegative integers")


def process_peak_rss() -> int:
    """Actual process-lifetime RSS high-water, not isolated stage memory."""
    import sys

    if sys.platform == "win32":
        return psutil.Process().memory_info().peak_wset
    import resource

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


def materialize_views(record: NormalizedEntity) -> RetrievalTextViews:
    name = record.business_name_normalized
    address = record.business_address_normalized
    # Historical compact removes ASCII spaces only, preserving tabs/newlines.
    return RetrievalTextViews(record.entity_id, name or "", (name or "").replace(" ", ""),
                              address or "", name or "", address or "",
                              name is None, address is None)


def vectorizer(view: str, config: RetrievalConfig) -> TfidfVectorizer:
    base = dict(min_df=config.min_df, max_df=config.max_df, sublinear_tf=True,
                dtype=np.float32, lowercase=False, norm="l2", use_idf=True, smooth_idf=True)
    if view == "name":
        return TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 3), **base)
    if view == "compact":
        return TfidfVectorizer(analyzer="char", ngram_range=(3, 3), **base)
    if view == "address":
        return TfidfVectorizer(analyzer="word", token_pattern=r"[a-z0-9]+", **base)
    raise ValueError("combined/reverse reuse name and address vectorizers")


def union_candidates(parts: tuple[RetrievalCandidate, ...]) -> tuple[RetrievalCandidate, ...]:
    combined = {}
    for candidate in parts:
        key = candidate.s1_id, candidate.target_id
        if key not in combined:
            combined[key] = candidate, {}
        first, evidence = combined[key]
        if (first.country, first.target_source) != (candidate.country, candidate.target_source):
            raise ValueError("candidate union has conflicting source/country")
        for e in candidate.lane_evidence:
            if e.lane in evidence:
                raise ValueError("duplicate lane hit for a pair")
            evidence[e.lane] = e
    result = []
    for first, evidence in combined.values():
        entries = tuple(evidence[lane] for lane in LANES if lane in evidence)
        mask = sum(1 << LANES.index(e.lane) for e in entries)
        result.append(RetrievalCandidate(first.s1_id, first.target_id, first.target_source,
                                         first.country, mask, entries))
    return canonical_candidates(result)


def retrieve(records: tuple[NormalizedEntity, ...],
             config: RetrievalConfig | None = None) -> RetrievalRun:
    config = config or RetrievalConfig()
    start, cpu_start = time.perf_counter(), time.process_time()
    process = psutil.Process()
    rss = process.memory_info().rss
    keys = [(r.source, r.entity_id) for r in records]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate normalized entity key")
    targets = [r.entity_id for r in records if r.source != "S1"]
    if len(set(targets)) != len(targets):
        raise ValueError("S2/S3 target IDs must be unique for the (s1_id,target_id) contract")
    rows = sorted(records, key=lambda r: (r.source, r.entity_id))
    countries = sorted({r.country for r in rows}, key=lambda x: (x is not None, x or ""))
    parts, fits, warnings = [], [], []
    eligible, bound = 0, 0
    for country in countries:
        queries = [r for r in rows if r.source == "S1" and r.country == country]
        targets = [r for r in rows if r.source != "S1" and r.country == country]
        eligible += len(queries) * len(targets)
        bound += len(queries) * sum(config.budgets[LANES.index(lane)]
                                    for lane in config.lanes if lane != "reverse")
        if "reverse" in config.lanes:
            bound += len(targets) * config.budgets[4]
        if not queries or not targets:
            warnings.append(f"country={country!r}: no queries or no eligible targets")
            continue
        qviews = [materialize_views(r) for r in queries]
        tviews = [materialize_views(r) for r in targets]
        matrices = {}
        for view in ("name", "compact", "address"):
            qa, ta = [getattr(r, view) for r in qviews], [getattr(r, view) for r in tviews]
            text = qa + ta
            selected = (np.arange(len(text)) if len(text) <= config.fit_cap else
                        np.sort(np.random.default_rng(config.seed).choice(
                            len(text), size=config.fit_cap, replace=False)))
            identities = [("S1", r.entity_id) for r in queries] + [
                (r.source, r.entity_id) for r in targets]
            sample_hash = content_sha256([identities[int(i)] for i in selected])
            v = vectorizer(view, config)
            try:
                v.fit([text[int(i)] for i in selected])
            except ValueError as exc:
                if not any(message in str(exc) for message in (
                        "empty vocabulary", "After pruning, no terms remain",
                        "max_df corresponds to < documents than min_df")):
                    raise
                # An explicit empty lane, never a relaxed-DF or all-pairs fallback.
                warnings.append(f"country={country!r} view={view}: {exc}")
                qm = sp.csr_matrix((len(queries), 0), dtype=np.float32)
                tm = sp.csr_matrix((len(targets), 0), dtype=np.float32)
                vocabulary = 0
            else:
                qm, tm = v.transform(qa).astype(np.float32), v.transform(ta).astype(np.float32)
                vocabulary = len(v.vocabulary_)
            matrices[view] = qm, tm
            fits.append(FitEvidence(country, view, sample_hash, len(selected), vocabulary,
                                    qm.nnz, tm.nnz))
            rss = max(rss, process.memory_info().rss)
        weight = np.float32(np.sqrt(.5))
        matrices["combined"] = tuple(sp.hstack([
            matrices["name"][i].multiply(weight), matrices["address"][i].multiply(weight),
        ]).tocsr() for i in (0, 1))
        for lane in config.lanes:
            reverse = lane == "reverse"
            qm, tm = matrices["combined" if reverse else lane]
            left, right = (tm, qm) if reverse else (qm, tm)
            if left.shape[1] == 0:
                continue
            right_t = right.T.tocsr()
            k = config.budgets[LANES.index(lane)]
            for offset in range(0, left.shape[0], config.chunk_size):
                hits = sp_matmul_topn(left[offset:offset + config.chunk_size], right_t,
                                     top_n=k, threshold=0.0, sort=True,
                                     n_threads=config.threads).tocsr()
                rss = max(rss, process.memory_info().rss)
                for local in range(hits.shape[0]):
                    indices = range(hits.indptr[local], hits.indptr[local + 1])
                    # Canonical input order also makes top-N cutoff ties repeatable.
                    ordered = sorted(indices, key=lambda j: (
                        -float(hits.data[j]),
                        (queries if reverse else targets)[int(hits.indices[j])].entity_id,
                    ))
                    for rank, j in enumerate(ordered, 1):
                        i, other = offset + local, int(hits.indices[j])
                        query, target = ((queries[other], targets[i]) if reverse
                                         else (queries[i], targets[other]))
                        e = LaneEvidence(lane, rank, float(hits.data[j]))
                        parts.append(RetrievalCandidate(query.entity_id, target.entity_id,
                                                        target.source, country,
                                                        1 << LANES.index(lane), (e,)))
        rss = max(rss, process.memory_info().rss)
    candidates = union_candidates(tuple(parts))
    if len(candidates) > min(bound, eligible):
        raise RuntimeError("candidate graph exceeded the bounded retrieval contract")
    return RetrievalRun(candidates, config, tuple(fits), tuple(warnings),
                        time.perf_counter() - start, time.process_time() - cpu_start,
                        max(rss, process.memory_info().rss), process_peak_rss(), eligible, bound)
