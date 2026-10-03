"""The non-null reference fold, with explicit null and Unicode version semantics."""

import unicodedata

from concord.contracts import EntityRecord, NormalizedEntity, optional_text

NORMALIZATION_VERSION = f"concord.fold.v1.ucd-{unicodedata.unidata_version}"


def normalize_text(value: str | None) -> str | None:
    optional_text(value)
    if value is None:
        return None
    return "".join(c for c in unicodedata.normalize("NFKD", value)
                   if not unicodedata.combining(c)).casefold()


def normalize(record: EntityRecord) -> NormalizedEntity:
    return NormalizedEntity(
        record.entity_id, record.source, record.business_name, record.business_address,
        normalize_text(record.business_name), normalize_text(record.business_address),
        record.country, NORMALIZATION_VERSION,
    )
