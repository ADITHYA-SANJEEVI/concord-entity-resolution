"""Obviously invented P0 records; declared entity-disjoint splits are committed JSON.

This corpus exercises a reference model, not benchmark quality or scale claims.
The training population is deliberately large enough for min_child_samples=100.
Held-out cases include retrieval/scoring/ownership misses and conflicting labels.
"""

from pathlib import Path

from concord.contracts import EntityRecord
from concord.identity import canonical_records
from concord.metadata import read_json
from concord.modeling.training import load_plan


def fixture():
    records, truths = [], {"train": [], "calibration": [], "test": []}

    def add(eid, source, name, address, country):
        records.append(EntityRecord(eid, source, name, address, country))

    for role, count in (("train", 240), ("calibration", 12)):
        country = f"INVENTED_{role.upper()}"
        for i in range(count):
            q, t, n = f"{role}-q-{i:03d}", f"{role}-t-{i:03d}", f"{role}-n-{i:03d}"
            name, address = f"Workshop {role} {i:03d} Cedar Repairs", f"{i + 10} Fable Avenue"
            qname, qaddress = name, address
            if role == "calibration" and i in (8, 9):
                qname, qaddress = name + " Limited", f"{i + 2000} Novel Road"
            if role == "calibration" and i == 10:
                qname, qaddress = None, None
            add(q, "S1", qname, qaddress, country)
            add(t, "S2" if i % 2 == 0 else "S3", name, address, country)
            add(n, "S3" if i % 2 == 0 else "S2", name + " Annex", f"{i + 1010} Myth Street", country)
            if role == "train" or i < 10:
                truths[role].append((q, t))

    country = "INVENTED_TEST"
    for i in range(6):
        q, t, n = f"test-q-{i:03d}", f"test-t-{i:03d}", f"test-n-{i:03d}"
        name, address = f"Workshop heldout {i:03d} Cedar Repairs", f"{i + 80} Fable Avenue"
        add(q, "S1", name, address, country)
        add(t, "S2", name, address, country)
        add(n, "S3", name + " Annex", f"{i + 4010} Myth Street", country)
        truths["test"].append((q, t))
    for suffix in ("one", "two"):
        add(f"test-multi-{suffix}", "S2", "Workshop Twin Cedar Repairs", "90 Fable Avenue", country)
        truths["test"].append(("test-multi", f"test-multi-{suffix}"))
    add("test-multi", "S1", "Workshop Twin Cedar Repairs", "90 Fable Avenue", country)
    for prefix in ("own", "amb"):
        add(f"test-{prefix}-target", "S3", f"Workshop {prefix} Cedar Repairs", "91 Fable Avenue", country)
        for suffix in ("a", "z"):
            add(f"test-{prefix}-{suffix}", "S1", f"Workshop {prefix} Cedar Repairs", "91 Fable Avenue", country)
        truths["test"].append((f"test-{prefix}-z", f"test-{prefix}-target"))
        if prefix == "amb":
            truths["test"].append(("test-amb-a", "test-amb-target"))
    add("test-miss", "S1", "कांचघर", None, "INVENTED_MISS")
    add("test-miss-target", "S2", "Quartz Polar Observatory", None, "INVENTED_MISS")
    truths["test"].append(("test-miss", "test-miss-target"))
    add("test-below", "S1", "Workshop Mist Cedar Repairs", "501 Novel Road", country)
    add("test-below-target", "S2", "Workshop Mist Cedar Repairs Annex", "700 Myth Street", country)
    truths["test"].append(("test-below", "test-below-target"))
    add("test-empty", "S1", None, "", country)
    add("test-phantom", "S1", "Workshop Phantom Cedar Repairs", "93 Fable Avenue", country)
    add("test-phantom-target", "S3", "Workshop Phantom Cedar Repairs", "93 Fable Avenue", country)
    add("test-partial", "S1", "Workshop Partial Cedar Repairs", "94 Fable Avenue", country)
    add("test-partial-exact", "S2", "Workshop Partial Cedar Repairs", "94 Fable Avenue", country)
    add("test-partial-miss", "S3", "Workshop Partial Cedar Repairs Annex", "904 Novel Road", country)
    truths["test"].extend((('test-partial', 'test-partial-exact'), ('test-partial', 'test-partial-miss')))
    return canonical_records(records), {role: tuple(sorted(pairs)) for role, pairs in truths.items()}


def split_plan():
    return load_plan(read_json(Path(__file__).with_name("pass_b_splits.json")))


def ambiguity_annotations():
    return (("test-amb-z", "test-amb-target",
             "Invented labels assign one target to two S1s although the ownership policy is exclusive"),)
