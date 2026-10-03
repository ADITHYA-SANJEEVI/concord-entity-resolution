import copy
import json
from dataclasses import FrozenInstanceError, asdict, replace

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from jsonschema import ValidationError

from concord.contracts import EntityRecord, NormalizedEntity
from concord.identity import canonical_records, dataset_fingerprint, split_fingerprint
from concord.inspection import profile
from concord.metadata import (
    ArtifactLineage,
    canonical_json,
    content_sha256,
    validate_lineage,
    validate_manifest,
    write_json,
)
from concord.normalization import NORMALIZATION_VERSION, normalize, normalize_text
from concord.storage import (
    ENTITY_SCHEMA,
    read_entities,
    read_fixture_tsv,
    read_normalized,
    write_entities,
    write_normalized,
)


@pytest.mark.parametrize("text", ["", "Café", "Cafe\u0301", "Straße", "İstanbul", "ＡＢＣ",
                                  "मैसूर टेक्सटाइल्स", "東京", "العربية", " a\t b \n", "Åﬃ",
                                  "NULL", "nan", "None", "Å & Co., Ltd.", "🙂"])
def test_nonnull_reference_fold_parity(text, reference_functions):
    assert normalize_text(text) == reference_functions["fold"](text)


def test_null_adaptation_is_explicit(reference_functions):
    assert reference_functions["fold"](None) == ""
    assert normalize_text(None) is None
    assert normalize_text("") == ""
    assert normalize_text("Café") == normalize_text("Cafe\u0301")


@pytest.mark.parametrize("value", [False, 1, 1.5, [], {}, float("nan")])
def test_text_type_rejected(value):
    with pytest.raises(ValueError):
        normalize_text(value)
    with pytest.raises(ValueError):
        EntityRecord("a", "S1", value, None)


@pytest.mark.parametrize("entity_id", ["", " ", "\n", None, 12])
def test_invalid_opaque_ids(entity_id):
    with pytest.raises(ValueError):
        EntityRecord(entity_id, "S1", None, "")


def test_immutable_optional_country_and_normalization():
    raw = EntityRecord("0/no-prefix", "S3", "  Café, Inc.  ", None)
    norm = normalize(raw)
    assert norm.country is None
    assert norm.business_address_normalized is None
    assert norm.business_name_normalized == "  cafe, inc.  "
    assert "compact" not in asdict(norm)
    assert norm.normalization_version == NORMALIZATION_VERSION
    for value in (raw, norm):
        with pytest.raises(FrozenInstanceError):
            value.entity_id = "new"
    with pytest.raises(ValueError):
        replace(raw, source="S4")
    with pytest.raises(ValueError):
        replace(norm, normalization_version="unknown")
    with pytest.raises(ValueError):
        replace(norm, business_name_normalized="cafe")
    assert isinstance(norm, NormalizedEntity)


def test_logical_identity(public_fixture, tmp_path):
    records, _ = public_fixture
    digest = dataset_fingerprint(records)
    assert digest == dataset_fingerprint(reversed(records))
    write_entities(tmp_path / "a.parquet", records)
    # Write a physically reversed table using the same contract.
    pq.write_table(pa.Table.from_pylist([asdict(r) for r in reversed(records)],
                                      schema=ENTITY_SCHEMA), tmp_path / "b.parquet")
    assert digest == dataset_fingerprint(read_entities(tmp_path / "b.parquet"))
    assert digest == dataset_fingerprint(read_entities(tmp_path / "a.parquet"))
    changed = (replace(records[0], business_name=""),) + records[1:]
    assert digest != dataset_fingerprint(changed)
    a = EntityRecord("x", "S1", None, "")
    assert dataset_fingerprint((a,)) != dataset_fingerprint((replace(a, business_name=""),))
    with pytest.raises(ValueError):
        dataset_fingerprint((a, a))
    # Identity is (source,id), not a guessed prefix or global ID assumption.
    assert len(canonical_records((a, replace(a, source="S2")))) == 2


def test_split_identity(public_fixture):
    rows, _ = public_fixture
    dataset = dataset_fingerprint(rows)
    members = tuple((r.source, r.entity_id) for r in rows if r.source == "S1")
    fp = split_fingerprint(dataset, "dev", "retrieval", members, {"b": 2, "a": 1})
    assert fp == split_fingerprint(dataset, "dev", "retrieval", reversed(members),
                                   {"a": 1, "b": 2})
    for name, purpose, keys in (("test", "retrieval", members), ("dev", "other", members),
                                ("dev", "retrieval", members[:-1])):
        assert fp != split_fingerprint(dataset, name, purpose, keys, {"a": 1, "b": 2})
    assert fp != split_fingerprint("a" * 64, "dev", "retrieval", members, {"a": 1, "b": 2})
    with pytest.raises(ValueError):
        split_fingerprint(dataset, "dev", "retrieval", members + members)


@pytest.mark.parametrize("records", [(), (EntityRecord("opaque", "S1", None, ""),),
                                    (EntityRecord("字", "S2", "Café\nLtd", None, "India"),)])
def test_parquet_roundtrip(records, tmp_path):
    write_entities(tmp_path / "entities.parquet", records)
    assert read_entities(tmp_path / "entities.parquet") == canonical_records(records)
    normalized = tuple(normalize(r) for r in records)
    write_normalized(tmp_path / "normalized.parquet", normalized)
    assert read_normalized(tmp_path / "normalized.parquet") == normalized


def test_invalid_parquet(tmp_path):
    path = tmp_path / "wrong.parquet"
    pq.write_table(pa.table({"entity_id": ["x"]}), path)
    with pytest.raises(ValueError):
        read_entities(path)
    row = asdict(EntityRecord("x", "S1", None, ""))
    row["entity_id"] = None
    with pytest.raises(pa.ArrowInvalid):
        pq.write_table(pa.Table.from_pylist([row], schema=ENTITY_SCHEMA), path)


def test_canonical_utf8(tmp_path):
    a = {"z": "मैसूर", "a": {"b": None, "c": ""}}
    b = {"a": {"c": "", "b": None}, "z": "मैसूर"}
    assert canonical_json(a) == canonical_json(b)
    write_json(tmp_path / "a.json", a)
    assert (tmp_path / "a.json").read_bytes() == canonical_json(a) + b"\n"
    assert json.loads(canonical_json(a)) == a
    assert content_sha256(a) == content_sha256(b)


@pytest.mark.parametrize("bad", [{1: "x"}, {"x": float("nan")}, {"x": float("inf")},
                                {"x": {"inner": float("-inf")}}, {"x": object()}])
def test_invalid_canonical_json(bad):
    with pytest.raises(ValueError):
        canonical_json(bad)


def test_tsv_explicit_boundary(tmp_path):
    path = tmp_path / "fixture.tsv"
    path.write_text("id\tname\taddress\nx\tNULL\t\n", encoding="utf-8")
    row, = read_fixture_tsv(path, "S3")
    assert row.business_name == "NULL" and row.business_address == "" and row.country is None
    path.write_text("id\tname\taddress\nx\tname\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_fixture_tsv(path, "S1")


def test_profile_missingness(public_fixture):
    records, _ = public_fixture
    result = profile(records)
    assert result["rows"] == len(records)
    assert result["fields"]["business_name"]["missing"] == 2
    assert result["fields"]["business_name"]["empty"] == 1
    assert any(r["label"] is None for r in result["countries"])
    assert profile(())["fields"]["business_name"]["length"]["mean"] is None


def test_lineage_dag():
    a = ArtifactLineage("a" * 64, ("b" * 64,), "c" * 64, "d" * 40, "v1", "retrieve", "D")
    b = replace(a, artifact_sha256="b" * 64, parent_sha256=())
    validate_lineage((a, b))
    with pytest.raises(ValueError):
        validate_lineage((a, replace(b, parent_sha256=("a" * 64,))))
    with pytest.raises(ValueError):
        replace(a, parent_sha256=["b" * 64])
    with pytest.raises(ValueError):
        replace(a, parent_sha256=("a" * 64,))
    validate_lineage((a, a))  # repeated producing observations share a content node
    with pytest.raises(ValueError):
        replace(a, stage=["mutable"])


def test_manifest_separate_schema():
    instance = {
        "schema_version": "concord.experiment.v1", "experiment_id": "planned",
        "timestamp_utc": "2026-10-03T00:00:00Z", "git": {"commit_sha": "a" * 40, "dirty": False},
        "provenance": {"dataset_fingerprint": "b" * 64, "split_fingerprint": None,
                       "dataset_track": "SYNTHETIC_PUBLIC", "population": "P0/planned"},
        "configuration_fingerprint": content_sha256({}), "pipeline_configuration": {},
        "metrics": {}, "operational": {}, "artifacts": {},
        "evidence": {"class": "E", "notes": []}, "disposition": "PLANNED",
    }
    validate_manifest(instance)
    assert "$schema" not in instance
    for field, value in (("schema_version", "unknown"), ("disposition", "PASS"),
                         ("metrics", {"recall": .9})):
        bad = copy.deepcopy(instance)
        bad[field] = value
        with pytest.raises(ValidationError):
            validate_manifest(bad)
    bad = copy.deepcopy(instance)
    bad["configuration_fingerprint"] = "c" * 64
    with pytest.raises(ValueError):
        validate_manifest(bad)
