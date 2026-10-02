"""Strict typed C3 Parquet products, with immutable contracts on every read."""

import json
from dataclasses import asdict

import pyarrow as pa

from concord.c3_contracts import (
    FEATURE_VERSION,
    CandidateDisposition,
    FailureAttribution,
    FeatureRow,
    OwnershipResult,
    ResolutionDecision,
    ScoredCandidate,
)
from concord.features.reference import FEATURE_NAMES, FEATURE_SCHEMA_SHA256
from concord.metadata import canonical_json
from concord.modeling.training import MinedPair
from concord.storage import _read, _write

S, F, B, INTEGER = pa.string(), pa.float64(), pa.bool_(), pa.int32()
PAIR_FIELDS = [("s1_id", S, False), ("target_id", S, False)]
DEFINITIONS = {
    "features": (FeatureRow, FEATURE_VERSION, PAIR_FIELDS + [(name, F, False) for name in FEATURE_NAMES]
                 + [("schema_version", S, False), ("schema_sha256", S, False)]),
    "scores": (ScoredCandidate, "concord.scored-candidate.v1", PAIR_FIELDS + [
        ("target_source", S, False), ("score", F, False), ("model_sha256", S, False), ("model_version", S, False)]),
    "ownership": (OwnershipResult, "concord.ownership-result.v1", PAIR_FIELDS + [
        ("score", F, False), ("is_owner", B, False), ("owner_rank", INTEGER, False), ("rival_s1_id", S, True),
        ("rival_score", F, True), ("rival_margin", F, True), ("ownership_policy_version", S, False)]),
    "candidate_dispositions": (CandidateDisposition, "concord.candidate-disposition.v1", PAIR_FIELDS + [
        ("score", F, False), ("is_owner", B, False), ("threshold", F, False), ("threshold_margin", F, False),
        ("accepted", B, False), ("rejection_reason", S, False), ("decoder_version", S, False)]),
    "resolutions": (ResolutionDecision, "concord.resolution-decision.v1", [
        ("s1_id", S, False), ("accepted_targets", pa.list_(pa.field("element", S, False)), False),
        ("decision_type", S, False), ("decoder_version", S, False)]),
    "failure_attribution": (FailureAttribution, "concord.failure-attribution-row.v1", PAIR_FIELDS + [
        ("error_type", S, False), ("failure_stage", S, False), ("tags", pa.list_(pa.field("element", S, False)), False),
        ("diagnostics", S, False), ("attribution_policy_version", S, False)]),
    "negatives": (MinedPair, "concord.mined-pair.v1", PAIR_FIELDS + [
        ("label", pa.int8(), False), ("reason", S, False), ("retrieval_config_sha256", S, False),
        ("candidate_graph_sha256", S, False), ("split_fingerprint", S, False), ("negative_config_sha256", S, False)]),
}
SCHEMAS = {name: pa.schema([pa.field(n, t, nullable) for n, t, nullable in fields], metadata={
    b"concord.schema_version": version.encode(),
    **({b"concord.feature_schema_sha256": FEATURE_SCHEMA_SHA256.encode()} if name == "features" else {})})
    for name, (_, version, fields) in DEFINITIONS.items()}


def _ordered(rows, stage):
    kind = DEFINITIONS[stage][0]
    if any(type(row) is not kind for row in rows):
        raise ValueError("stage artifact contains a different contract")
    keys = [(r.s1_id,) if stage == "resolutions" else (r.s1_id, r.target_id) for r in rows]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate artifact key")
    return tuple(r for _, r in sorted(zip(keys, rows, strict=True), key=lambda p: p[0]))


def write_stage(path, stage: str, rows: tuple) -> None:
    values = []
    for row in _ordered(rows, stage):
        value = asdict(row)
        if stage == "features":
            if row.schema_sha256 != FEATURE_SCHEMA_SHA256:
                raise ValueError("feature schema mismatch")
            value.update(zip(FEATURE_NAMES, value.pop("values"), strict=True))
        elif stage == "failure_attribution":
            value["diagnostics"] = canonical_json(value["diagnostics"]).decode("utf-8")
        values.append(value)
    _write(path, values, SCHEMAS[stage])


def read_stage(path, stage: str) -> tuple:
    rows = []
    for value in _read(path, SCHEMAS[stage]):
        if stage == "features":
            value["values"] = tuple(value.pop(name) for name in FEATURE_NAMES)
            if value["schema_sha256"] != FEATURE_SCHEMA_SHA256:
                raise ValueError("feature schema mismatch")
        elif stage == "resolutions":
            value["accepted_targets"] = tuple(value["accepted_targets"])
        elif stage == "failure_attribution":
            value["tags"] = tuple(value["tags"])
            value["diagnostics"] = tuple(tuple(pair) for pair in json.loads(value["diagnostics"]))
        rows.append(DEFINITIONS[stage][0](**value))
    return _ordered(tuple(rows), stage)
