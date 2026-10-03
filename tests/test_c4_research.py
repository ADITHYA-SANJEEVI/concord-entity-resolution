"""C4 regression tests for experimental isolation, evidence and actual replay."""

from argparse import Namespace
from dataclasses import asdict, replace

import numpy as np
import pyarrow.parquet as pq
import pytest

from concord.c3_cli import verified_run
from concord.features.reference import FEATURE_NAMES, FEATURE_SCHEMA_SHA256, generate_features
from concord.identity import dataset_fingerprint
from concord.metadata import content_sha256, read_json, validate_manifest
from concord.normalization import normalize
from concord.research.definitions import (
    GROUPS,
    ExperimentDefinition,
    ScaleObservation,
    StabilityObservation,
    experiment_suite,
)
from concord.research.experiments import candidate_graph, run_suite
from concord.research.fixtures import PERTURBATIONS, perturb, public_fixture, workload
from concord.research.reports import ATLAS_SCHEMA, FailureAtlasEntry
from concord.research.scale import SCALE_SCHEMA, run_scale
from concord.research.scorers import ResearchScorer
from concord.research.statistics import paired_mean_interval, risk_comparison, risk_metrics
from concord.storage import read_entities


@pytest.mark.parametrize("group,indices", GROUPS)
def test_ablation_identity_and_order(group, indices):
    definition = ExperimentDefinition("without_" + group, removed_group=group)
    matrix = np.arange(118, dtype=np.float32).reshape(2, 59)
    masked = definition.matrix(matrix)
    assert not masked[:, indices].any()
    rest = [i for i in range(59) if i not in indices]
    np.testing.assert_array_equal(masked[:, rest], matrix[:, rest])
    assert definition.sha256 == ExperimentDefinition(**asdict(definition)).sha256
    assert definition.sha256 != ExperimentDefinition("reference").sha256
    assert len(FEATURE_NAMES) == 59


@pytest.mark.parametrize("values", [{"retrieval": "cartesian"}, {"seed": 7}, {"removed_group": "made_up"}, {"scorer": "llm"}])
def test_definition_rejects_unbounded_or_changed_reference(values):
    with pytest.raises(ValueError):
        ExperimentDefinition("bad", **values)


def test_logistic_fit_load_determinism_and_training_scaler():
    rng = np.random.default_rng(19)
    X = rng.normal(size=(160, 59)).astype(np.float32)
    y = (X[:, 0] > 0).astype(int)
    definition = ExperimentDefinition("logistic", scorer="logistic")
    a, b = ResearchScorer(definition).fit(X, y), ResearchScorer(definition).fit(X, y)
    assert a.fingerprint() == b.fingerprint()
    loaded = ResearchScorer.load(read_json_payload(a.payload))
    test = X * 17 + 4
    np.testing.assert_array_equal(a.predict_proba(test), loaded.predict_proba(test))
    np.testing.assert_allclose(a.predict_proba(test), a.logistic.predict_proba(a.scaler.transform(test))[:, 1], atol=1e-14)
    assert a.payload["fitted"]["mean"] == b.payload["fitted"]["mean"]
    broken = dict(a.payload, feature_schema_sha256="0" * 64)
    with pytest.raises(ValueError, match="schema"):
        ResearchScorer.load(broken)


def read_json_payload(payload):
    import json

    return json.loads(json.dumps(payload))


def test_split_isolation_and_public_identity():
    fixture = public_fixture()
    selected = [fixture.selected(role)[0] for role in ("train", "calibration", "test")]
    identities = [{(r.source, r.entity_id) for r in rows} for rows in selected]
    assert not identities[0] & identities[1] and not identities[0] & identities[2] and not identities[1] & identities[2]
    assert fixture.plan == public_fixture().plan
    assert dataset_fingerprint(tuple(reversed(fixture.records))) == fixture.plan.dataset_fingerprint
    assert len([r for r in selected[2] if r.source == "S1"]) == 133
    for role in ("train", "calibration", "test"):
        rows, truth = fixture.selected(role)
        assert all(q in {r.entity_id for r in rows if r.source == "S1"} and t in {r.entity_id for r in rows if r.source != "S1"} for q, t in truth)


@pytest.mark.parametrize("name", PERTURBATIONS)
def test_perturbation_scope_and_determinism(name):
    rows, _ = workload(16, "test")
    a, b = perturb(rows, name), perturb(tuple(reversed(rows)), name)
    assert a == b
    assert {r for r in rows if r.source != "S1"} == {r for r in a if r.source != "S1"}
    assert len(a) == len(rows) + (name == "competition")
    original = {r.entity_id: r for r in rows}
    assert all(r.business_name is None for r in a if r.entity_id in original and original[r.entity_id].business_name is None)


def test_actual_retrieval_features_row_order_and_bounded_rescue():
    rows, _ = workload(16)
    candidates, config, identity, baseline, extra, origins = candidate_graph(rows, "transliterated_name")
    reversed_candidates, *_ = candidate_graph(tuple(reversed(rows)), "transliterated_name")
    assert candidates == reversed_candidates
    assert len(candidates) <= len(baseline.candidates) + 16 * 5
    assert extra is not None and identity != config.fingerprint
    assert origins["original_pairs"] + origins["rescued_pairs"] == len(candidates)
    assert generate_features(tuple(normalize(r) for r in rows), candidates, config) == generate_features(tuple(normalize(r) for r in reversed(rows)), candidates, config)


def test_metric_edge_cases_and_paired_interval():
    assert paired_mean_interval([0, 1], [1, 1])["delta"] == .5
    perfect = risk_metrics(("a", "b", "c", "d"), [0, 0, 1, 1], [.1, .2, .8, .9])
    assert perfect["auroc_error"] == perfect["auprc_error"] == 1
    assert perfect["risk_at_90"] == .5
    assert risk_metrics(("a",), [0], [.2])["auroc_error"] is None
    result = risk_comparison(("a", "b", "c", "d"), [0, 0, 1, 1], [.1, .2, .8, .9], [.1, .2, .8, .9], repetitions=30)
    assert result["paired_auroc_delta_ci95"] == [0, 0]
    assert result["conclusion"] == "no clear evidence of difference"
    for a, b in (([], []), ([0], [float("nan")])):
        with pytest.raises(ValueError):
            paired_mean_interval(a, b)


def test_observation_validation_and_immutability():
    valid = ScaleObservation(2, 4, 8, 0, "pipeline", .01, 1024, 512, 2)
    with pytest.raises(ValueError):
        replace(valid, wall_seconds=0)
    with pytest.raises(ValueError):
        replace(valid, samples=1)
    with pytest.raises(ValueError):
        StabilityObservation("q", "case", ["t"], ())
    with pytest.raises(ValueError):
        StabilityObservation("q", "case", ("z", "a"), ())


@pytest.fixture(scope="module")
def executed(tmp_path_factory):
    out = tmp_path_factory.mktemp("c4")
    args = Namespace(output=str(out / "public"), run_id="c4-test", population="P0/c4/test", track="SYNTHETIC_PUBLIC")
    summary = run_suite(args)
    scale = run_scale(Namespace(output=str(out / "scale"), model_run=args.output, run_id="c4-test-scale", population="P0/c4/scale", track="SYNTHETIC_PUBLIC", sizes="16,32", repetitions=2, warmups=1))
    return out, summary, scale


def test_completed_suite_lineage_and_frozen_decisions(executed):
    out, summary, _ = executed
    manifest = verified_run(out / "public")
    validate_manifest(manifest)
    assert len(summary["experiments"]) == len(experiment_suite()) == 12
    assert summary["repeat_equal"] and summary["row_order_equal"]
    reference = summary["experiments"]["reference"]["roles"]["test"]
    assert reference["quality"]["query_count"] == 133
    assert reference["feature_schema_sha256"] == FEATURE_SCHEMA_SHA256
    # Regression: robustness must never overwrite the frozen reference graph.
    assert read_entities(out / "public/graphs/reference/test/entities.parquet") == public_fixture().selected("test")[0]
    for name in PERTURBATIONS:
        assert f"graphs/reference/perturbation-{name}/candidates.parquet" in manifest["artifacts"]
        observations = read_json(out / f"public/robustness/{name}/observations.json")
        changed = sum(r["reference_targets"] != r["perturbed_targets"] for r in observations)
        assert summary["robustness"][name]["changed_count"] == changed
    capsules = read_json(out / "public/reference/test/capsules.json")
    assert all("is_stable" not in c for c in capsules)


def test_failure_atlas_actual_attribution_and_serialization(executed):
    out, summary, _ = executed
    table = pq.read_table(out / "public/reference/test/atlas.parquet")
    assert table.schema.equals(ATLAS_SCHEMA, check_metadata=True)
    report = summary["experiments"]["reference"]["roles"]["test"]
    assert table.num_rows == report["quality"]["fp"] + report["quality"]["fn"]
    assert {r["error_type"] for r in table.to_pylist()} == {"FALSE_NEGATIVE", "FALSE_POSITIVE"}
    for row in table.to_pylist():
        row["truth_targets"], row["accepted_targets"] = tuple(row["truth_targets"]), tuple(row["accepted_targets"])
        entry = FailureAtlasEntry(**row)
        assert content_sha256(asdict(entry))
    with pytest.raises(ValueError):
        replace(entry, failure_stage="ROOT_CAUSE")


def test_executed_scale_validity_and_hash_tamper(executed):
    out, _, scale = executed
    manifest = verified_run(out / "scale")
    table = pq.read_table(out / "scale/observations.parquet")
    assert table.schema.equals(SCALE_SCHEMA, check_metadata=True)
    assert table.num_rows == 2 * 2 * 8
    assert set(scale["workloads"]) == {"16", "32"}
    for row in table.to_pylist():
        assert ScaleObservation(**row).samples >= 2
    model = out / "scale/reference_model.json"
    payload = model.read_bytes()
    model.write_bytes(payload + b" ")
    with pytest.raises(ValueError, match="hash"):
        verified_run(out / "scale")
    model.write_bytes(payload)
    assert manifest == verified_run(out / "scale")
