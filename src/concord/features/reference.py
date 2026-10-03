"""59-feature reference on a bounded C2 graph, never an all-pairs product.

Reference numeric adapters (empty/missing text, zero-based ranks and absent=999)
are confined to model features. Raw records and C2 lane evidence stay lossless.
Exact cosines are recomputed on supplied pairs using the declared C2 fit policy.
"""

import re
import unicodedata
from collections import defaultdict
from dataclasses import asdict, dataclass

import numpy as np
import scipy.sparse as sp
from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler
from unidecode import unidecode

from concord.c3_contracts import FEATURE_VERSION, FeatureRow
from concord.contracts import LANES, NormalizedEntity, RetrievalCandidate
from concord.metadata import content_sha256
from concord.retrieval.baseline import (
    RetrievalConfig,
    _fit_sample_positions,
    materialize_views,
    vectorizer,
)
from concord.storage import canonical_candidates

FEATURE_NAMES = (
    "name_nonempty_exact_match", "name_normalized_string_ratio", "name_jaro_winkler",
    "name_token_sort_ratio", "name_token_set_ratio", "name_partial_ratio",
    "name_char_trigram_jaccard", "name_token_jaccard", "name_query_token_coverage",
    "name_target_token_coverage", "address_nonempty_exact_match", "address_normalized_string_ratio",
    "address_token_sort_ratio", "address_token_set_ratio", "address_char_trigram_jaccard",
    "address_token_jaccard", "address_query_token_coverage", "address_target_token_coverage",
    "numeric_token_jaccard", "numeric_query_coverage", "numeric_target_coverage",
    "nonempty_first_number_equality", "query_numeric_token_count", "target_numeric_token_count",
    "query_name_missing", "target_name_missing", "query_address_missing", "target_address_missing",
    "target_source_is_S2", "exact_name_cosine", "exact_compact_name_cosine", "exact_address_cosine",
    "exact_combined_cosine", "name_rank", "compact_name_rank", "address_rank", "combined_rank",
    "reverse_rank", "name_query_source_rank", "name_query_source_delta_best",
    "name_target_owner_rank", "name_target_delta_best", "name_target_rival_margin",
    "address_query_source_rank", "address_query_source_delta_best", "address_target_owner_rank",
    "address_target_delta_best", "address_target_rival_margin", "combined_query_source_rank",
    "combined_query_source_delta_best", "combined_target_owner_rank", "combined_target_delta_best",
    "combined_target_rival_margin", "candidate_count_within_s1_source",
    "distinct_competing_s1_count_for_target", "f55", "f56", "f57", "f58",
)
_DIRECT_DEFINITIONS = (
    "nonempty normalized name equality", "RapidFuzz ratio /100; empty side=0",
    "RapidFuzz JaroWinkler normalized_similarity; empty side=0",
    "RapidFuzz token_sort_ratio /100; empty side=0", "RapidFuzz token_set_ratio /100; empty side=0",
    "RapidFuzz partial_ratio /100; empty side=0", "unique name character-trigram Jaccard",
    "Unicode word-token name Jaccard", "name token intersection / query token count",
    "name token intersection / target token count", "nonempty normalized address equality",
    "address RapidFuzz ratio /100; empty side=0", "address token_sort_ratio /100; empty side=0",
    "address token_set_ratio /100; empty side=0", "unique address character-trigram Jaccard",
    "Unicode word-token address Jaccard", "address intersection / query token count",
    "address intersection / target token count", "unique address digit-token Jaccard",
    "numeric intersection / query unique count", "numeric intersection / target unique count",
    "nonempty first address digit-token equality", "query unique address digit-token count",
    "target unique address digit-token count", "query normalized name empty-or-missing indicator",
    "target normalized name empty-or-missing indicator", "query address empty-or-missing indicator",
    "target address empty-or-missing indicator", "explicit target source equals S2",
)
_DEFINITIONS = _DIRECT_DEFINITIONS + (
    "pair dot product: C2 float32 L2 name TF-IDF", "pair dot product: C2 compact TF-IDF",
    "pair dot product: C2 address TF-IDF", "float32 .5*name_cosine + .5*address_cosine",
) + tuple(f"{lane}: C2 one-based rank minus one; absent numeric feature=999" for lane in LANES) + tuple(
    f"{signal}: {description}" for signal in ("name", "address", "combined") for description in (
        "SQL RANK by exact cosine DESC within (s1_id,target_source); ties share rank",
        "exact cosine minus maximum within (s1_id,target_source)",
        "SQL RANK by exact cosine DESC within target_id; ties share rank",
        "exact cosine minus target maximum",
        "singleton=0; unique maximum minus second; otherwise score minus maximum",
    )) + (
    "retrieved pair count within (s1_id,target_source)", "distinct competing S1 count within target_id",
    "raw names: Unidecode lower unique trigram Jaccard; empty/empty=0",
    "raw names: max ratio/100 over original/transliterated lower combinations; empty/empty=0",
    "raw names: dominant Unicode name prefix differs, both not UNKNOWN; first-seen tie wins",
    "raw addresses: Unidecode lower [a-z0-9]+ token Jaccard; empty/empty=0",
)


@dataclass(frozen=True, slots=True)
class FeatureDefinition:
    name: str
    definition: str
    definition_version: str = "reference-reference-adapter.v1"

    def __post_init__(self):
        if any(not isinstance(v, str) or not v for v in (
                self.name, self.definition, self.definition_version)):
            raise ValueError("feature names and definitions must be explicit")


@dataclass(frozen=True, slots=True)
class FeatureSchema:
    ordered_features: tuple[FeatureDefinition, ...]
    schema_version: str = FEATURE_VERSION

    def __post_init__(self):
        if (type(self.ordered_features) is not tuple or len(self.ordered_features) != 59
                or any(not isinstance(f, FeatureDefinition) for f in self.ordered_features)
                or len({f.name for f in self.ordered_features}) != 59):
            raise ValueError("schema needs 59 unique ordered immutable definitions")
        if self.schema_version != FEATURE_VERSION:
            raise ValueError("unknown feature schema version")

    @property
    def sha256(self):
        return content_sha256(asdict(self))


REFERENCE_SCHEMA = FeatureSchema(tuple(FeatureDefinition(name, definition)
                                      for name, definition in zip(FEATURE_NAMES, _DEFINITIONS, strict=True)))
FEATURE_SCHEMA_SHA256 = REFERENCE_SCHEMA.sha256
WORD, NUM = re.compile(r"\w+", re.UNICODE), re.compile(r"\d+")


def trigrams(value: str) -> frozenset[str]:
    return frozenset(value[i:i + 3] for i in range(max(0, len(value) - 2)))


def overlap(a, b):
    hit, union = len(a & b), len(a | b)
    return (hit / union if union else 0., hit / len(a) if a else 0., hit / len(b) if b else 0.)


def direct_features(qname: str, qaddr: str, tname: str, taddr: str, source: str) -> tuple[float, ...]:
    qn, tn = frozenset(WORD.findall(qname)), frozenset(WORD.findall(tname))
    qa, ta = frozenset(WORD.findall(qaddr)), frozenset(WORD.findall(taddr))
    qnumbers, tnumbers = NUM.findall(qaddr), NUM.findall(taddr)
    qs, ts = frozenset(qnumbers), frozenset(tnumbers)
    nj, nqc, ntc = overlap(qn, tn)
    aj, aqc, atc = overlap(qa, ta)
    numj, numqc, numtc = overlap(qs, ts)
    names = (fuzz.ratio(qname, tname) / 100, JaroWinkler.normalized_similarity(qname, tname),
             fuzz.token_sort_ratio(qname, tname) / 100, fuzz.token_set_ratio(qname, tname) / 100,
             fuzz.partial_ratio(qname, tname) / 100) if qname and tname else (0.,) * 5
    addresses = (fuzz.ratio(qaddr, taddr) / 100, fuzz.token_sort_ratio(qaddr, taddr) / 100,
                 fuzz.token_set_ratio(qaddr, taddr) / 100) if qaddr and taddr else (0.,) * 3
    return (float(bool(qname) and qname == tname), *names,
            overlap(trigrams(qname), trigrams(tname))[0], nj, nqc, ntc,
            float(bool(qaddr) and qaddr == taddr), *addresses,
            overlap(trigrams(qaddr), trigrams(taddr))[0], aj, aqc, atc,
            numj, numqc, numtc, float(bool(qnumbers) and bool(tnumbers) and qnumbers[0] == tnumbers[0]),
            float(len(qs)), float(len(ts)), float(not qname), float(not tname),
            float(not qaddr), float(not taddr), float(source == "S2"))


def dominant_script(text: str) -> str:
    counts = {}
    for char in text:
        if char.isalpha():
            prefix = unicodedata.name(char, "").split()
            if prefix:
                counts[prefix[0]] = counts.get(prefix[0], 0) + 1
    return max(counts, key=counts.get) if counts else "UNKNOWN"


def cross_features(qname: str | None, qaddr: str | None,
                   tname: str | None, taddr: str | None) -> tuple[float, ...]:
    qn, qa, tn, ta = qname or "", qaddr or "", tname or "", taddr or ""
    qt, tt = unidecode(qn).lower(), unidecode(tn).lower()
    ratios = (fuzz.ratio(a, b) / 100 for a in (qn.lower(), qt) for b in (tn.lower(), tt))
    qs, ts = dominant_script(qn), dominant_script(tn)
    return (overlap(trigrams(qt), trigrams(tt))[0], max(ratios) if qn or tn else 0.,
            float(qs != ts and qs != "UNKNOWN" and ts != "UNKNOWN"),
            overlap(frozenset(re.findall(r"[a-z0-9]+", unidecode(qa).lower())),
                    frozenset(re.findall(r"[a-z0-9]+", unidecode(ta).lower())))[0])


def context_features(candidates, cosines) -> dict[tuple[str, str], tuple[float, ...]]:
    """Match the reference SQL RANK/MAX/unique-top rival semantics, including ties."""
    query_groups, target_groups = defaultdict(list), defaultdict(list)
    for c in candidates:
        query_groups[c.s1_id, c.target_source].append((c.s1_id, c.target_id))
        target_groups[c.target_id].append((c.s1_id, c.target_id))
    result = {}
    for c in candidates:
        key, values = (c.s1_id, c.target_id), []
        qkeys, tkeys = query_groups[c.s1_id, c.target_source], target_groups[c.target_id]
        for index in (0, 2, 3):
            score = cosines[key][index]
            qvalues, tvalues = [cosines[k][index] for k in qkeys], [cosines[k][index] for k in tkeys]
            qbest, tbest = max(qvalues), max(tvalues)
            lower = [v for v in tvalues if v < tbest]
            margin = (0. if len(tvalues) == 1 else
                      score - max(lower) if score == tbest and tvalues.count(tbest) == 1 else score - tbest)
            values.extend((float(1 + sum(v > score for v in qvalues)), score - qbest,
                           float(1 + sum(v > score for v in tvalues)), score - tbest, margin))
        result[key] = (*values, float(len(qkeys)), float(len(tkeys)))
    return result


def generate_features(records: tuple[NormalizedEntity, ...], candidates: tuple[RetrievalCandidate, ...],
                      config: RetrievalConfig) -> tuple[FeatureRow, ...]:
    candidates = canonical_candidates(candidates)
    keys = {(r.source, r.entity_id): r for r in records}
    if len(keys) != len(records):
        raise ValueError("duplicate normalized records")
    targets = [r.entity_id for r in records if r.source != "S1"]
    if len(set(targets)) != len(targets):
        raise ValueError("ambiguous target IDs")
    for c in candidates:
        q, t = keys.get(("S1", c.s1_id)), keys.get((c.target_source, c.target_id))
        if q is None or t is None or q.country != t.country or c.country != q.country:
            raise ValueError("candidate does not belong to the supplied eligible records")
    cosines = {}
    for country in sorted({c.country for c in candidates}, key=lambda v: (v is not None, v or "")):
        q = sorted((r for r in records if r.source == "S1" and r.country == country), key=lambda r: r.entity_id)
        t = sorted((r for r in records if r.source != "S1" and r.country == country), key=lambda r: (r.source, r.entity_id))
        pairs = [c for c in candidates if c.country == country]
        qmap, tmap = {r.entity_id: i for i, r in enumerate(q)}, {r.entity_id: i for i, r in enumerate(t)}
        qi, ti = np.array([qmap[c.s1_id] for c in pairs]), np.array([tmap[c.target_id] for c in pairs])
        qviews, tviews = [materialize_views(r) for r in q], [materialize_views(r) for r in t]
        exact = []
        for view in ("name", "compact", "address"):
            qa, ta = [getattr(r, view) for r in qviews], [getattr(r, view) for r in tviews]
            text = qa + ta
            selected = _fit_sample_positions(len(text), config)
            v = vectorizer(view, config)
            try:
                v.fit([text[int(i)] for i in selected])
            except ValueError as exc:
                if not any(s in str(exc) for s in ("empty vocabulary", "After pruning, no terms remain",
                                                  "max_df corresponds to < documents than min_df")):
                    raise
                qm, tm = sp.csr_matrix((len(q), 0), dtype=np.float32), sp.csr_matrix((len(t), 0), dtype=np.float32)
            else:
                qm, tm = v.transform(qa).astype(np.float32), v.transform(ta).astype(np.float32)
            # Coordinate-only products: memory proportional to retrieved edges, no expansion.
            exact.append(np.asarray(qm[qi].multiply(tm[ti]).sum(axis=1)).ravel().astype(np.float32))
        combined = np.float32(.5) * exact[0] + np.float32(.5) * exact[2]
        for i, c in enumerate(pairs):
            cosines[c.s1_id, c.target_id] = tuple(float(v[i]) for v in (*exact, combined))
    context = context_features(candidates, cosines)
    rows = []
    for c in candidates:
        q, t = keys["S1", c.s1_id], keys[c.target_source, c.target_id]
        lanes = {e.lane: e.rank for e in c.lane_evidence}
        values = (*direct_features(q.business_name_normalized or "", q.business_address_normalized or "",
                                  t.business_name_normalized or "", t.business_address_normalized or "", c.target_source),
                  *cosines[c.s1_id, c.target_id],
                  *(float(lanes[lane] - 1) if lane in lanes else 999. for lane in LANES),
                  *context[c.s1_id, c.target_id],
                  *cross_features(q.business_name_raw, q.business_address_raw, t.business_name_raw, t.business_address_raw))
        rows.append(FeatureRow(c.s1_id, c.target_id, tuple(values), FEATURE_VERSION, FEATURE_SCHEMA_SHA256))
    return tuple(rows)


def feature_matrix(rows: tuple[FeatureRow, ...]) -> np.ndarray:
    if any(r.schema_version != FEATURE_VERSION or r.schema_sha256 != FEATURE_SCHEMA_SHA256 for r in rows):
        raise ValueError("model/feature schema mismatch")
    if len({(r.s1_id, r.target_id) for r in rows}) != len(rows):
        raise ValueError("duplicate feature pair")
    matrix = np.array([r.values for r in rows], dtype=np.float32).reshape(-1, 59)
    if not np.isfinite(matrix).all():
        raise ValueError("feature overflow at float32 model boundary")
    return matrix
