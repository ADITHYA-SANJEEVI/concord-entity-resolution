"""Logical identities independent of file order, paths, and platform newlines."""

import hashlib
from collections.abc import Iterable
from dataclasses import asdict

from concord.contracts import ENTITY_VERSION, EntityRecord, Source, require_id
from concord.metadata import canonical_json, content_sha256, require_sha256


def canonical_records(records: Iterable[EntityRecord]) -> tuple[EntityRecord, ...]:
    rows = tuple(sorted(records, key=lambda r: (r.source, r.entity_id)))
    keys = [(r.source, r.entity_id) for r in rows]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate (source, entity_id)")
    return rows


def dataset_fingerprint(records: Iterable[EntityRecord]) -> str:
    digest = hashlib.sha256()
    digest.update(canonical_json({"schema_version": ENTITY_VERSION}) + b"\n")
    for record in canonical_records(records):
        digest.update(canonical_json(asdict(record)) + b"\n")
    return digest.hexdigest()


def split_fingerprint(dataset_sha256: str, name: str, purpose: str,
                      members: Iterable[tuple[Source, str]],
                      cohort_metadata: dict | None = None) -> str:
    require_sha256(dataset_sha256)
    if not isinstance(name, str) or not name or not isinstance(purpose, str) or not purpose:
        raise ValueError("split name and purpose are required")
    keys = tuple(members)
    for source, entity_id in keys:
        if source not in ("S1", "S2", "S3"):
            raise ValueError("invalid split source")
        require_id(entity_id)
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate split member")
    return content_sha256({
        "schema_version": "concord.split.v1", "dataset_fingerprint": dataset_sha256,
        "name": name, "purpose": purpose, "members": sorted(keys),
        "cohort_metadata": cohort_metadata,
    })
