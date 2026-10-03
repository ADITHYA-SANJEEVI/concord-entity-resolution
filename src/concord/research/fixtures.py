"""Invented multilingual P0 workload; explicit recipe roles, never a random split."""

from dataclasses import dataclass, replace

from concord.contracts import EntityRecord
from concord.identity import canonical_records, dataset_fingerprint
from concord.modeling.training import SplitGroup, SplitPlan

RECIPE_VERSION = "concord.p0.multilingual-c4.v1"
ROLE_COUNTS = (("train", 320), ("calibration", 64), ("test", 128))
PERTURBATIONS = ("case", "spacing", "punctuation", "token_order", "transliteration", "competition")
NAMES = (("Лунная лавка", "Lunnaya lavka"), ("Φανταστική αγορά", "Phantastike agora"),
         ("कल्पना दुकान", "kalpanaa dukaan"), ("空想商店", "Kong Xiang Shang Dian"))


@dataclass(frozen=True, slots=True)
class PublicFixture:
    records: tuple[EntityRecord, ...]
    truth: tuple[tuple[str, str], ...]
    plan: SplitPlan
    ambiguities: tuple[tuple[str, str, str], ...]

    def selected(self, role):
        records = self.plan.select(self.records, role)
        queries = {r.entity_id for r in records if r.source == "S1"}
        return records, tuple(pair for pair in self.truth if pair[0] in queries)


def workload(count: int, role: str = "scale"):
    if type(count) is not int or count < 1 or count > 4096:
        raise ValueError("public workload query count must be 1..4096")
    rows, truth = [], []
    for i in range(count):
        qid, tid, nid = f"{role}-q-{i:04d}", f"{role}-t-{i:04d}", f"{role}-n-{i:04d}"
        pattern = i % 16
        label = f"Fable {role} Emporium {i:04d}"
        qname, tname = label, label
        address = f"{1000 + i} Invented Lantern Road"
        qaddr, taddr = address, address
        country = "P0-OOD" if role == "test" and pattern in (4, 9) else "P0-SEEN"
        if pattern in (3, 4, 5, 10):
            qname, tname = NAMES[(pattern // 2) % len(NAMES)]
            qname, tname = f"{qname} {i:04d}", f"{tname} {i:04d}"
            if pattern == 10:
                qaddr = taddr = None
        elif pattern == 1:
            qname = " ".join(reversed(label.split()))
        elif pattern == 2:
            qname = label.replace(" ", " - ")
        elif pattern == 7:
            qaddr = taddr = None
        elif pattern == 8:
            qname = tname = None
        elif pattern == 9:
            qaddr = address.replace("Road", "Rd")
        elif pattern == 13:
            tname = label.replace("Emporium", "Market")
        elif pattern == 15:
            qname, tname, qaddr, taddr = "χψω", "xyz", None, None
        rows.extend((EntityRecord(qid, "S1", qname, qaddr, country),
                     EntityRecord(tid, "S2", tname, taddr, country),
                     EntityRecord(nid, "S3", tname, f"{9000 + i} Fictional Quay", country)))
        if pattern != 6:
            truth.append((qid, tid))
        if pattern == 11:
            extra = f"{role}-extra-{i:04d}"
            rows.append(EntityRecord(extra, "S3", tname, taddr, country))
            truth.append((qid, extra))
    return canonical_records(rows), tuple(sorted(truth))


def public_fixture():
    rows, truths, ambiguities, groups = [], [], [], []
    for role, count in ROLE_COUNTS:
        selected, truth = workload(count, role)
        if role == "test":
            special = (
                EntityRecord("test-own-a", "S1", "Invented Ownership Bazaar", "17 Fable Sq", "P0-SEEN"),
                EntityRecord("test-own-z", "S1", "Invented Ownership Bazaar", "17 Fable Sq", "P0-SEEN"),
                EntityRecord("test-own-target", "S2", "Invented Ownership Bazaar", "17 Fable Sq", "P0-SEEN"),
                EntityRecord("test-amb-a", "S1", "Imaginary Ambiguous Shop", "19 Fable Sq", "P0-SEEN"),
                EntityRecord("test-amb-z", "S1", "Imaginary Ambiguous Shop", "19 Fable Sq", "P0-SEEN"),
                EntityRecord("test-amb-target", "S3", "Imaginary Ambiguous Shop", "19 Fable Sq", "P0-SEEN"),
                EntityRecord("test-empty", "S1", None, None, "P0-SEEN"),
            )
            selected = canonical_records(selected + special)
            truth += (("test-own-z", "test-own-target"), ("test-amb-a", "test-amb-target"),
                      ("test-amb-z", "test-amb-target"))
            ambiguities = [(q, "test-amb-target", "explicit contradictory labels under exclusive target ownership")
                           for q in ("test-amb-a", "test-amb-z")]
        rows.extend(selected)
        truths.extend(truth)
        groups.append(SplitGroup(role, role, tuple(sorted((r.source, r.entity_id) for r in selected))))
    records = canonical_records(rows)
    return PublicFixture(records, tuple(sorted(truths)), SplitPlan(dataset_fingerprint(records), tuple(groups)), tuple(ambiguities))


def perturb(records, name):
    if name not in PERTURBATIONS:
        raise ValueError("unknown declared perturbation")
    from unidecode import unidecode

    result = []
    for row in records:
        if row.source != "S1":
            result.append(row)
            continue
        def text(value):
            if value is None:
                return None
            if name == "case":
                return value.swapcase()
            if name == "spacing":
                return "  " + value.replace(" ", "   ") + "  "
            if name == "punctuation":
                return value.replace(" ", " / ")
            if name == "token_order":
                return " ".join(reversed(value.split()))
            if name == "transliteration":
                return unidecode(value)
            return value
        result.append(replace(row, business_name=text(row.business_name), business_address=text(row.business_address)))
    if name == "competition":
        original = next(r for r in canonical_records(records) if r.source == "S1" and r.business_name)
        result.append(replace(original, entity_id="!injected-public-competitor"))
    return canonical_records(result)
