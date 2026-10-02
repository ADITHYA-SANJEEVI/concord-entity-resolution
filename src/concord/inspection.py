"""Small, deterministic dataset profiles for the C1 inspection surface."""

import unicodedata
from collections import Counter

import numpy as np

from concord.contracts import ENTITY_VERSION, EntityRecord
from concord.identity import canonical_records, dataset_fingerprint
from concord.normalization import NORMALIZATION_VERSION


def profile(records: tuple[EntityRecord, ...]) -> dict:
    records = canonical_records(records)
    fields = {}
    for field in ("business_name", "business_address"):
        values = [getattr(r, field) for r in records]
        lengths = [len(v) for v in values if v is not None]
        scripts = Counter()
        for value in values:
            # Unicode-name families, explicitly diagnostic rather than ISO 15924 claims.
            families = {unicodedata.name(c, "UNKNOWN").split()[0]
                        for c in value or "" if c.isalpha()}
            scripts.update(families)
        fields[field] = {
            "missing": sum(v is None for v in values), "empty": sum(v == "" for v in values),
            "length": {"mean": float(np.mean(lengths)) if lengths else None,
                       "p50": float(np.quantile(lengths, .5)) if lengths else None,
                       "max": max(lengths) if lengths else None},
            "unicode_name_families": dict(sorted(scripts.items())),
        }
    countries = Counter(r.country for r in records)
    return {
        "schema_version": ENTITY_VERSION, "normalization_version": NORMALIZATION_VERSION,
        "dataset_fingerprint": dataset_fingerprint(records), "rows": len(records),
        "sources": dict(sorted(Counter(r.source for r in records).items())),
        "countries": [{"label": label, "rows": countries[label]}
                      for label in sorted(countries, key=lambda x: (x is not None, x or ""))],
        "fields": fields,
    }
