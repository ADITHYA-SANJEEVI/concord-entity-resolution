"""Invented P0 retrieval records. No organizer or external benchmark data."""

from concord.contracts import EntityRecord


def fixture() -> tuple[tuple[EntityRecord, ...], tuple[tuple[str, str], ...]]:
    rows = (
        EntityRecord("query/name", "S1", "Maple Works", None, "US"),
        EntityRecord("query/address", "S1", None, "18 Harbor Road", "US"),
        EntityRecord("query/compact", "S1", "Delta Labs", "", "US"),
        EntityRecord("query/both", "S1", "North Wind Bakery", "8 Pine Street", "US"),
        EntityRecord("query/script", "S1", "मैसूर टेक्सटाइल्स", "12 मार्केट रोड", "India"),
        EntityRecord("query/accent", "S1", "Café Élan", None),
        EntityRecord("query/missing", "S1", None, None),
        EntityRecord("query/multi", "S1", "Blue Orbit", "9 Lake Avenue", "US"),
        EntityRecord("query/miss", "S1", "दुर्गा सिल्क्स", "बाजार", "India"),
        EntityRecord("target/name", "S2", "Maple Works", None, "US"),
        EntityRecord("target/address", "S2", "Unrelated Trading", "18 Harbor Road", "US"),
        EntityRecord("target/compact", "S3", "DeltaLabs", "", "US"),
        EntityRecord("target/both", "S2", "Northwind Bakery", "8 Pine St", "US"),
        EntityRecord("target/script", "S3", "मैसूर टेक्सटाइल्स", "", "India"),
        EntityRecord("target/accent", "S2", "CAFE ELAN", None),
        EntityRecord("target/multi-a", "S2", "Blue Orbit", "9 Lake Avenue", "US"),
        EntityRecord("target/multi-b", "S3", "Blue Orbit Limited", "9 Lake Ave", "US"),
        EntityRecord("target/miss", "S2", "Durga Silks", "Market", "India"),
        EntityRecord("target/noise-a", "S3", "Maple Garage", "7 Harbor Lane", "US"),
        EntityRecord("target/noise-b", "S3", "Pine Traders", "18 Pine Road", "US"),
        EntityRecord("target/empty", "S3", "", ""),
    )
    truth = tuple((f"query/{name}", f"target/{name}") for name in (
        "name", "address", "compact", "both", "script", "accent", "miss")) + (
        ("query/multi", "target/multi-a"), ("query/multi", "target/multi-b"),
    )
    return rows, truth


def historical_fixture() -> tuple[tuple[EntityRecord, ...], tuple[tuple[str, str], ...]]:
    """Larger invented corpus that exercises the strict historical DF cutoffs."""
    rows, truth = [], []
    for i in range(200):
        name, address = f"brand{i:04x}", f"location{i:04x}"
        query, target = f"q{i:03d}", f"t{i:03d}"
        rows.extend((EntityRecord(query, "S1", name, address, "US"),
                     EntityRecord(target, "S2", name, address, "US")))
        truth.append((query, target))
    return tuple(rows), tuple(truth)
