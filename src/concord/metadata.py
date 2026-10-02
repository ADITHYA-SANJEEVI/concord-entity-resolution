"""Canonical metadata, manifest validation, and content-addressed lineage primitives."""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from importlib.resources import files
from pathlib import Path

from jsonschema import Draft202012Validator


def canonical_json(value: object) -> bytes:
    def check(item: object) -> None:
        if isinstance(item, dict):
            if any(not isinstance(k, str) for k in item):
                raise ValueError("JSON object keys must be strings")
            for v in item.values():
                check(v)
        elif isinstance(item, (list, tuple)):
            for v in item:
                check(v)
        elif item is not None and type(item) not in (str, int, float, bool):
            raise ValueError("unsupported JSON value")

    check(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def content_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def write_json(path: str | Path, value: object) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value) + b"\n")


def read_json(path: str | Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def require_sha256(value: str) -> None:
    if (not isinstance(value, str) or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value)):
        raise ValueError("expected a lowercase SHA-256 identity")


@dataclass(frozen=True, slots=True)
class ArtifactLineage:
    artifact_sha256: str
    parent_sha256: tuple[str, ...]
    configuration_sha256: str
    code_commit: str
    schema_version: str
    stage: str
    evidence_class: str

    def __post_init__(self) -> None:
        require_sha256(self.artifact_sha256)
        require_sha256(self.configuration_sha256)
        if type(self.parent_sha256) is not tuple:
            raise ValueError("parents must be an immutable tuple")
        for parent in self.parent_sha256:
            require_sha256(parent)
        if len(set(self.parent_sha256)) != len(self.parent_sha256):
            raise ValueError("duplicate lineage parent")
        if self.artifact_sha256 in self.parent_sha256:
            raise ValueError("artifact cannot parent itself")
        if (not isinstance(self.code_commit, str) or len(self.code_commit) != 40
                or any(c not in "0123456789abcdef" for c in self.code_commit)):
            raise ValueError("lineage requires the full producing Git commit")
        if self.evidence_class not in ("A", "B", "C", "D", "E"):
            raise ValueError("unknown evidence class")
        if (not isinstance(self.schema_version, str) or not self.schema_version
                or not isinstance(self.stage, str) or not self.stage):
            raise ValueError("schema and stage are required")


def validate_lineage(records: tuple[ArtifactLineage, ...]) -> None:
    """Validate the content DAG, retaining multiple producing observations per hash.

    Different configurations can produce identical bytes. Their lineage records
    remain separate observations; the DAG merges content nodes and parent edges.
    External parent identities are allowed.
    """
    nodes: dict[str, set[str]] = {}
    for record in records:
        nodes.setdefault(record.artifact_sha256, set()).update(record.parent_sha256)
    visited, active = set(), set()

    def visit(key: str) -> None:
        if key in active:
            raise ValueError("lineage cycle")
        if key in visited or key not in nodes:
            return
        active.add(key)
        for parent in nodes[key]:
            visit(parent)
        active.remove(key)
        visited.add(key)

    for key in nodes:
        visit(key)


def validate_manifest(instance: dict) -> None:
    serialized = json.loads(canonical_json(instance))  # validate the actual JSON representation
    schema = json.loads(files("concord").joinpath("schemas/experiment.schema.json")
                        .read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(serialized)
    datetime.fromisoformat(instance["timestamp_utc"].replace("Z", "+00:00"))
    if instance["configuration_fingerprint"] != content_sha256(instance["pipeline_configuration"]):
        raise ValueError("manifest configuration fingerprint mismatch")
    for name, metric in instance["metrics"].items():
        if metric["name"] != name:
            raise ValueError("metric name must agree with its manifest key")
        if metric["producing_run"] != instance["experiment_id"]:
            raise ValueError("metric must identify the producing run")
    records = []
    for artifact in instance["artifacts"].values():
        fields = dict(artifact["lineage"])
        fields["parent_sha256"] = tuple(fields["parent_sha256"])
        record = ArtifactLineage(**fields)
        if record.artifact_sha256 != artifact["sha256"]:
            raise ValueError("artifact and lineage identity mismatch")
        records.append(record)
    validate_lineage(tuple(records))


def lineage_dict(record: ArtifactLineage) -> dict:
    return asdict(record)
