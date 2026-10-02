"""Strict versioned Parquet tables; TSV is only an explicit external adapter."""

import csv
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from concord.contracts import (
    ENTITY_VERSION,
    LANES,
    EntityRecord,
    LaneEvidence,
    NormalizedEntity,
    RetrievalCandidate,
    Source,
)
from concord.identity import canonical_records


def _schema(fields: list[tuple[str, bool]], version: str) -> pa.Schema:
    return pa.schema([pa.field(name, pa.string(), nullable=nullable) for name, nullable in fields],
                     metadata={b"concord.schema_version": version.encode("ascii")})


ENTITY_SCHEMA = _schema([
    ("entity_id", False), ("source", False), ("business_name", True),
    ("business_address", True), ("country", True), ("schema_version", False),
], ENTITY_VERSION)
NORMALIZED_SCHEMA = _schema([
    ("entity_id", False), ("source", False), ("business_name_raw", True),
    ("business_address_raw", True), ("business_name_normalized", True),
    ("business_address_normalized", True), ("country", True), ("normalization_version", False),
], "concord.normalized-entity.v1")
CANDIDATE_SCHEMA = pa.schema([
    pa.field("s1_id", pa.string(), False), pa.field("target_id", pa.string(), False),
    pa.field("target_source", pa.string(), False), pa.field("country", pa.string()),
    pa.field("retrieval_view_mask", pa.uint8(), False),
    *[field for lane in LANES for field in (
        pa.field(f"{lane}_rank", pa.int32()), pa.field(f"{lane}_similarity", pa.float32()),
    )],
], metadata={b"concord.schema_version": b"concord.retrieval-candidate.v1"})


def _write(path: str | Path, rows: list[dict], schema: pa.Schema) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), path, compression="zstd")


def _read(path: str | Path, schema: pa.Schema) -> list[dict]:
    table = pq.read_table(path)
    if not table.schema.equals(schema, check_metadata=True):
        raise ValueError("Parquet schema/version differs from the Concord contract")
    for field in schema:
        if not field.nullable and table[field.name].null_count:
            raise ValueError(f"non-nullable column contains nulls: {field.name}")
    return table.to_pylist()


def write_entities(path: str | Path, records: Iterable[EntityRecord]) -> None:
    _write(path, [asdict(r) for r in canonical_records(records)], ENTITY_SCHEMA)


def read_entities(path: str | Path) -> tuple[EntityRecord, ...]:
    return canonical_records(EntityRecord(**r) for r in _read(path, ENTITY_SCHEMA))


def _normalized_rows(records: Iterable[NormalizedEntity]) -> tuple[NormalizedEntity, ...]:
    rows = tuple(sorted(records, key=lambda r: (r.source, r.entity_id)))
    if len({(r.source, r.entity_id) for r in rows}) != len(rows):
        raise ValueError("duplicate normalized entity")
    return rows


def write_normalized(path: str | Path, records: Iterable[NormalizedEntity]) -> None:
    _write(path, [asdict(r) for r in _normalized_rows(records)], NORMALIZED_SCHEMA)


def read_normalized(path: str | Path) -> tuple[NormalizedEntity, ...]:
    return _normalized_rows(NormalizedEntity(**r) for r in _read(path, NORMALIZED_SCHEMA))


def canonical_candidates(records: Iterable[RetrievalCandidate]) -> tuple[RetrievalCandidate, ...]:
    rows = tuple(sorted(records, key=lambda r: (r.s1_id, r.target_id)))
    if len({(r.s1_id, r.target_id) for r in rows}) != len(rows):
        raise ValueError("duplicate union candidate")
    return rows


def write_candidates(path: str | Path, records: Iterable[RetrievalCandidate]) -> None:
    rows = []
    for r in canonical_candidates(records):
        row = {"s1_id": r.s1_id, "target_id": r.target_id, "target_source": r.target_source,
               "country": r.country, "retrieval_view_mask": r.retrieval_view_mask}
        evidence = {e.lane: e for e in r.lane_evidence}
        for lane in LANES:
            e = evidence.get(lane)
            row[f"{lane}_rank"] = e.rank if e else None
            row[f"{lane}_similarity"] = e.similarity if e else None
        rows.append(row)
    _write(path, rows, CANDIDATE_SCHEMA)


def read_candidates(path: str | Path) -> tuple[RetrievalCandidate, ...]:
    candidates = []
    for row in _read(path, CANDIDATE_SCHEMA):
        evidence = []
        for lane in LANES:
            rank = row.pop(f"{lane}_rank")
            similarity = row.pop(f"{lane}_similarity")
            if (rank is None) != (similarity is None):
                raise ValueError("lane rank and similarity nullability disagree")
            if rank is not None:
                evidence.append(LaneEvidence(lane, rank, similarity))
        candidates.append(RetrievalCandidate(**row, lane_evidence=tuple(evidence)))
    return canonical_candidates(candidates)


def read_fixture_tsv(path: str | Path, source: Source) -> tuple[EntityRecord, ...]:
    """Present empty TSV cells stay empty; absent country columns mean None.

    TSV has no portable null encoding. Use Parquet for explicit missing text.
    No 'NULL', 'nan', or 'None' token is treated as missing.
    """
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not {"id", "name", "address"} <= set(reader.fieldnames):
            raise ValueError("fixture TSV requires id/name/address")
        records = []
        for row in reader:
            if None in row or any(row[key] is None for key in reader.fieldnames):
                raise ValueError("malformed TSV row")
            records.append(EntityRecord(row["id"], source, row["name"], row["address"],
                                        row.get("country")))
    return canonical_records(records)
