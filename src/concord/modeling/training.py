"""Explicit entity-disjoint splits and retrieval-only negative mining."""

from dataclasses import asdict, dataclass

from concord.contracts import EntityRecord, RetrievalCandidate, require_id
from concord.identity import dataset_fingerprint, split_fingerprint
from concord.metadata import content_sha256, require_sha256
from concord.retrieval.analysis import evaluate_retrieval
from concord.storage import canonical_candidates


@dataclass(frozen=True, slots=True)
class SplitGroup:
    name: str
    role: str
    members: tuple[tuple[str, str], ...]

    def __post_init__(self):
        require_id(self.name)
        if self.role not in ("train", "calibration", "test") or type(self.members) is not tuple:
            raise ValueError("explicit split role and immutable membership required")
        for member in self.members:
            if type(member) is not tuple or len(member) != 2 or member[0] not in ("S1", "S2", "S3"):
                raise ValueError("invalid split identity")
            require_id(member[1])
        if len(set(self.members)) != len(self.members) or self.members != tuple(sorted(self.members)):
            raise ValueError("split members must be sorted and unique")
        if not any(source == "S1" for source, _ in self.members):
            raise ValueError("split must contain explicit queries")


@dataclass(frozen=True, slots=True)
class SplitPlan:
    dataset_fingerprint: str
    groups: tuple[SplitGroup, ...]
    schema_version: str = "concord.c3.entity-disjoint-splits.v1"

    def __post_init__(self):
        require_sha256(self.dataset_fingerprint)
        if (type(self.groups) is not tuple or any(not isinstance(g, SplitGroup) for g in self.groups)
                or {g.role for g in self.groups} != {"train", "calibration", "test"}
                or len(self.groups) != 3 or len({g.name for g in self.groups}) != 3):
            raise ValueError("one explicit train/calibration/test group each required")
        members = [member for group in self.groups for member in group.members]
        if len(set(members)) != len(members):
            raise ValueError("entity leakage across split groups")
        target_ids = [eid for source, eid in members if source != "S1"]
        if len(target_ids) != len(set(target_ids)):
            raise ValueError("target IDs must be unambiguous across the plan")
        if self.schema_version != "concord.c3.entity-disjoint-splits.v1":
            raise ValueError("unsupported split policy")

    @property
    def sha256(self):
        return content_sha256(asdict(self))

    def group(self, name: str) -> SplitGroup:
        matches = [g for g in self.groups if g.name == name]
        if not matches:
            raise ValueError("unknown explicit split")
        return matches[0]

    def select(self, records: tuple[EntityRecord, ...], name: str) -> tuple[EntityRecord, ...]:
        if dataset_fingerprint(records) != self.dataset_fingerprint:
            raise ValueError("split plan belongs to a different logical dataset")
        if {m for g in self.groups for m in g.members} != {(r.source, r.entity_id) for r in records}:
            raise ValueError("plan membership must exactly cover the declared dataset")
        group = self.group(name)
        return tuple(r for r in records if (r.source, r.entity_id) in set(group.members))

    def split_sha256(self, name: str) -> str:
        group = self.group(name)
        return split_fingerprint(self.dataset_fingerprint, group.name, group.role, group.members,
                                 {"split_plan_sha256": self.sha256})


def load_plan(value: dict) -> SplitPlan:
    return SplitPlan(value["dataset_fingerprint"], tuple(SplitGroup(
        g["name"], g["role"], tuple(tuple(m) for m in g["members"])) for g in value["groups"]),
        value["schema_version"])


@dataclass(frozen=True, slots=True)
class NegativeConfig:
    strategy: str = "concord.top-retrieval-hard-negatives.v1"
    max_negatives_per_query: int = 16
    seed: int = 42

    def __post_init__(self):
        if self.strategy != "concord.top-retrieval-hard-negatives.v1":
            raise ValueError("unsupported negative policy")
        if type(self.max_negatives_per_query) is not int or self.max_negatives_per_query < 1:
            raise ValueError("negative cap must be positive")
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError("nonnegative seed required")

    @property
    def sha256(self):
        return content_sha256(asdict(self))


@dataclass(frozen=True, slots=True)
class MinedPair:
    s1_id: str
    target_id: str
    label: int
    reason: str
    retrieval_config_sha256: str
    candidate_graph_sha256: str
    split_fingerprint: str
    negative_config_sha256: str

    def __post_init__(self):
        require_id(self.s1_id)
        require_id(self.target_id)
        if type(self.label) is not int or self.label not in (0, 1):
            raise ValueError("binary label required")
        if self.reason != ("retrieved_labelled_truth" if self.label else "retrieved_not_labelled_truth_top_similarity"):
            raise ValueError("mining reason must agree with label")
        for digest in (self.retrieval_config_sha256, self.candidate_graph_sha256,
                       self.split_fingerprint, self.negative_config_sha256):
            require_sha256(digest)


def mine_negatives(records: tuple[EntityRecord, ...], candidates: tuple[RetrievalCandidate, ...],
                   truth: tuple[tuple[str, str], ...], plan: SplitPlan, split_name: str,
                   retrieval_sha256: str, graph_sha256: str,
                   config: NegativeConfig | None = None) -> tuple[MinedPair, ...]:
    config = config or NegativeConfig()
    group = plan.group(split_name)
    if group.role != "train":
        raise ValueError("only explicit training truth may be mined")
    if {(r.source, r.entity_id) for r in records} != set(group.members):
        raise ValueError("training records must match split membership exactly")
    evaluate_retrieval(records, candidates, truth)  # rejects held-out/unknown truth and graph pairs
    candidates = canonical_candidates(candidates)
    truths, kept = set(truth), []
    split_sha, config_sha = plan.split_sha256(split_name), config.sha256
    queries = sorted({c.s1_id for c in candidates})
    for query in queries:
        pairs = [c for c in candidates if c.s1_id == query]
        positive = [c for c in pairs if (c.s1_id, c.target_id) in truths]
        negative = sorted((c for c in pairs if (c.s1_id, c.target_id) not in truths), key=lambda c: (
            -max(e.similarity for e in c.lane_evidence),
            content_sha256([config.seed, c.s1_id, c.target_id])))[:config.max_negatives_per_query]
        for c in positive + negative:
            label = int((c.s1_id, c.target_id) in truths)
            kept.append(MinedPair(c.s1_id, c.target_id, label,
                                  "retrieved_labelled_truth" if label else "retrieved_not_labelled_truth_top_similarity",
                                  retrieval_sha256, graph_sha256, split_sha, config_sha))
    return tuple(sorted(kept, key=lambda p: (p.s1_id, p.target_id)))
