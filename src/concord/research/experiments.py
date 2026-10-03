"""Controlled P0 suite, preserving C1-C3 semantics and separate evidence parents."""

import time
from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np

from concord.c3_cli import retained_run
from concord.c3_storage import DEFINITIONS, write_stage
from concord.evaluation.failures import attribute_failures, failure_report
from concord.evaluation.quality import calibration_report, quality_report
from concord.features.reference import FEATURE_SCHEMA_SHA256, feature_matrix, generate_features
from concord.identity import dataset_fingerprint
from concord.inference.resolution import DecoderConfig, decode, evidence_capsules, global_ownership
from concord.inspection import profile
from concord.metadata import content_sha256, read_json
from concord.modeling.training import load_plan, mine_negatives
from concord.normalization import normalize
from concord.research.definitions import StabilityObservation, experiment_suite
from concord.research.fixtures import PERTURBATIONS, RECIPE_VERSION, perturb, public_fixture
from concord.research.reports import ATLAS_SCHEMA, atlas, cohort_members, cohorts, structure_inputs
from concord.research.scorers import ResearchScorer
from concord.research.statistics import paired_mean_interval, risk_comparison
from concord.retrieval.analysis import candidate_fingerprint, evaluate_retrieval
from concord.retrieval.baseline import retrieve, synthetic_config
from concord.storage import (
    _write,
    canonical_candidates,
    write_candidates,
    write_entities,
    write_normalized,
)


def config_for(mode):
    return synthetic_config(budgets=(1,) * 5) if mode == "k1" else synthetic_config(
        lanes=("name", "compact", "address", "combined")) if mode == "no_reverse" else synthetic_config()


def candidate_graph(records, mode):
    config = config_for(mode)
    baseline = retrieve(tuple(normalize(r) for r in records), config)
    origins = {}
    candidates, extra = baseline.candidates, None
    if mode == "transliterated_name":
        from unidecode import unidecode

        views = tuple(replace(r, business_name=unidecode(r.business_name) if r.business_name is not None else None) for r in records)
        extra = retrieve(tuple(normalize(r) for r in views), synthetic_config(lanes=("name",)))
        # Original provenance wins on overlap. Rescued rows carry the actual new
        # name-lane rank/similarity; origin metadata makes its representation explicit.
        original = {(c.s1_id, c.target_id): c for c in candidates}
        added = {(c.s1_id, c.target_id): c for c in extra.candidates}
        candidates = canonical_candidates(tuple((added | original).values()))
        origins = {"original_pairs": len(original), "rescued_pairs": len(set(added) - set(original)),
                   "overlap_pairs": len(set(added) & set(original)),
                   "origin_by_pair": [[c.s1_id, c.target_id, "original" if (c.s1_id, c.target_id) in original else "transliterated-name"] for c in candidates],
                   "view_dataset_fingerprint": dataset_fingerprint(views),
                   "adapter": "Unidecode names only, preserve None, then C1 normalize; top5 name lane.v1",
                   "rank_policy": "original C2 record on overlap; actual transliterated name record on rescue",
                   "transliterated_graph_sha256": candidate_fingerprint(extra.candidates),
                   "original_graph_sha256": candidate_fingerprint(baseline.candidates)}
    identity = config.fingerprint if extra is None else content_sha256({"base": config.fingerprint,
        "extra": extra.config.fingerprint, "adapter": origins["adapter"], "rank_policy": origins["rank_policy"]})
    return candidates, config, identity, baseline, extra, origins


def persist_table(run, prefix, stage, rows, parents):
    name = f"{prefix}/{stage}.parquet"
    (run.out / prefix).mkdir(parents=True, exist_ok=True)
    write_stage(run.out / name, stage, rows)
    return run.artifact(name, stage, DEFINITIONS[stage][1], parents)


def prepare(run, records, role, mode, truth, root_sha, split_sha):
    prefix = f"graphs/{mode}/{role}"
    (run.out / prefix).mkdir(parents=True, exist_ok=True)
    normalized = tuple(normalize(r) for r in records)
    write_entities(run.out / f"{prefix}/entities.parquet", records)
    entity_sha = run.artifact(f"{prefix}/entities.parquet", "split-ingest", "concord.entity.v1", (root_sha, split_sha))
    write_normalized(run.out / f"{prefix}/normalized.parquet", normalized)
    normalized_sha = run.artifact(f"{prefix}/normalized.parquet", "normalize", "concord.normalized-entity.v1", (entity_sha,))
    start = time.perf_counter()
    candidates, config, identity, original, extra, origins = candidate_graph(records, mode)
    retrieval_seconds = time.perf_counter() - start
    definition_sha = run.json(f"{prefix}/retrieval_definition.json", {"schema_version": "concord.c4.retrieval-definition.v1",
        "mode": mode, "configuration": asdict(config), "retrieval_identity_sha256": identity,
        "extra_configuration": asdict(extra.config) if extra else None, "origin": origins,
        "fit_evidence": [asdict(f) for f in original.fit_evidence], "warnings": list(original.warnings),
        "extra_fit_evidence": [asdict(f) for f in extra.fit_evidence] if extra else [],
        "extra_warnings": list(extra.warnings) if extra else []}, "retrieval-definition", (normalized_sha, identity))
    write_candidates(run.out / f"{prefix}/candidates.parquet", candidates)
    graph_sha = run.artifact(f"{prefix}/candidates.parquet", "retrieve", "concord.retrieval-candidate.v1", (definition_sha, normalized_sha))
    start = time.perf_counter()
    features = generate_features(normalized, candidates, config)
    feature_seconds = time.perf_counter() - start
    feature_sha = persist_table(run, prefix, "features", features, (graph_sha, FEATURE_SCHEMA_SHA256, normalized_sha))
    report = evaluate_retrieval(records, candidates, truth)
    run.json(f"{prefix}/retrieval_report.json", report, "retrieval-report", (graph_sha, split_sha))
    return {"records": records, "normalized": normalized, "candidates": candidates, "config": config,
            "retrieval_sha": identity, "graph_sha": graph_sha, "features": features, "feature_sha": feature_sha,
            "retrieval_seconds": retrieval_seconds, "feature_seconds": feature_seconds, "retrieval_report": report}


def execute_resolution(prepared, scorer, truth, split_sha, commit, ambiguities=(), population="P0/multilingual-c4/test"):
    from concord.modeling.scorer import score_features

    start = time.perf_counter()
    scores = score_features(prepared["features"], prepared["candidates"], scorer,
                            model_version="concord.c4.numeric-model.v1")
    owners = global_ownership(scores)
    queries = tuple(r.entity_id for r in prepared["records"] if r.source == "S1")
    dispositions, decisions = decode(owners, queries)
    capsules = evidence_capsules(prepared["candidates"], scores, owners, dispositions, decisions,
        dataset_sha=dataset_fingerprint(prepared["records"]), split_sha=split_sha,
        retrieval_sha=prepared["retrieval_sha"], feature_schema_sha=FEATURE_SCHEMA_SHA256,
        model_sha=scorer.fingerprint(), code_commit=commit)
    resolution_seconds = time.perf_counter() - start
    labels = set(truth)
    failures = attribute_failures(queries, truth, prepared["candidates"], scores, owners, dispositions, decisions, ambiguities)
    return {"scores": scores, "owners": owners, "dispositions": dispositions, "decisions": decisions,
            "capsules": capsules, "failures": failures, "resolution_seconds": resolution_seconds,
            "quality": quality_report(queries, truth, decisions, population),
            "calibration": calibration_report(tuple(int((s.s1_id, s.target_id) in labels) for s in scores), tuple(s.score for s in scores), population + "/retrieved-pairs"),
            "failure_report": failure_report(failures, population),
            "cohorts": cohorts(prepared["records"], truth, prepared["candidates"], scores, owners, decisions, population)}


def persist_resolution(run, prefix, prepared, result, truth_sha, model_sha, split_sha):
    score_sha = persist_table(run, prefix, "scores", result["scores"], (prepared["feature_sha"], model_sha))
    owner_sha = persist_table(run, prefix, "ownership", result["owners"], (score_sha,))
    disposition_sha = persist_table(run, prefix, "candidate_dispositions", result["dispositions"], (owner_sha, DecoderConfig().sha256))
    resolution_sha = persist_table(run, prefix, "resolutions", result["decisions"], (disposition_sha, split_sha))
    failure_sha = persist_table(run, prefix, "failure_attribution", result["failures"], (resolution_sha, prepared["graph_sha"], score_sha, owner_sha, truth_sha))
    capsule_sha = run.json(f"{prefix}/capsules.json", [asdict(c) for c in result["capsules"]], "resolution-evidence", (resolution_sha, score_sha, owner_sha, prepared["graph_sha"], model_sha, split_sha))
    identity = content_sha256({"model": model_sha, "dataset": dataset_fingerprint(prepared["records"]),
                              "split": split_sha, "retrieval": prepared["retrieval_sha"], "decoder": DecoderConfig().sha256,
                              "feature_schema": FEATURE_SCHEMA_SHA256})
    entries = atlas(prepared["records"], tuple(result["truth"]), prepared["candidates"], result["scores"],
                    result["owners"], result["dispositions"], result["decisions"], result["failures"], identity)
    _write(run.out / f"{prefix}/atlas.parquet", [asdict(e) for e in entries], ATLAS_SCHEMA)
    atlas_sha = run.artifact(f"{prefix}/atlas.parquet", "failure-atlas", "concord.c4.failure-atlas.v1", (failure_sha, capsule_sha, prepared["graph_sha"], truth_sha))
    report = {"schema_version": "concord.c4.result.v1", "population": result["quality"]["population"],
        "dataset_fingerprint": dataset_fingerprint(prepared["records"]), "split_fingerprint": split_sha,
        "retrieval_sha256": prepared["retrieval_sha"], "feature_schema_sha256": FEATURE_SCHEMA_SHA256,
        "model_sha256": model_sha, "decoder_sha256": DecoderConfig().sha256,
        "score_fingerprint": content_sha256([[s.s1_id, s.target_id, s.score] for s in result["scores"]]),
        "resolution_fingerprint": content_sha256([asdict(d) for d in result["decisions"]]),
        "quality": result["quality"], "calibration": result["calibration"], "failures": result["failure_report"],
        "cohorts": result["cohorts"], "resolution_seconds": result["resolution_seconds"],
        "candidate_count": len(prepared["candidates"]), "atlas_entry_count": len(entries)}
    run.json(f"{prefix}/result.json", report, "quality-calibration-cohorts", (resolution_sha, failure_sha, atlas_sha, truth_sha))
    return report, entries


def run_suite(args):
    from concord.research.scale import MEMORY_METHOD, RSSSampler

    fixture = public_fixture()
    committed = load_plan(read_json(Path(__file__).resolve().parents[3] / "examples/synthetic/pass_c_splits.json"))
    if committed != fixture.plan:
        raise ValueError("public recipe does not match the committed split plan")
    definitions = experiment_suite()
    config = {"stage": "c4-public", "recipe": RECIPE_VERSION, "definitions": [asdict(d) for d in definitions],
              "definition_identities": [d.sha256 for d in definitions], "split_plan_sha256": fixture.plan.sha256,
              "policy": asdict(DecoderConfig()), "bootstrap_seed": 2026, "auto_promotion": False}
    with retained_run(args, fixture.records, fixture.plan.sha256, config) as run:
        write_entities(run.out / "entities.parquet", fixture.records)
        root_sha = run.artifact("entities.parquet", "ingest", "concord.entity.v1", (dataset_fingerprint(fixture.records),))
        plan_sha = run.json("split_plan.json", asdict(fixture.plan), "split-policy", (root_sha,))
        truth_sha, selected = {}, {}
        for role in ("train", "calibration", "test"):
            selected[role] = fixture.selected(role)
            truth_sha[role] = run.json(f"truth_{role}.json", selected[role][1], "labels", (plan_sha, fixture.plan.split_sha256(role)))
        cache = {}
        results, models, summary, examples = {}, {}, {}, []
        for definition in definitions:
            for role, (records, truth) in selected.items():
                key = definition.retrieval, role
                if key not in cache:
                    cache[key] = prepare(run, records, role, definition.retrieval, truth, root_sha, fixture.plan.split_sha256(role))
            train = cache[definition.retrieval, "train"]
            mined = mine_negatives(train["records"], train["candidates"], selected["train"][1], fixture.plan, "train",
                                   train["retrieval_sha"], train["graph_sha"])
            prefix = definition.name
            (run.out / prefix).mkdir(parents=True, exist_ok=True)
            definition_sha = run.json(f"{prefix}/definition.json", {**asdict(definition), "definition_sha256": definition.sha256}, "experiment-definition", (plan_sha, definition.sha256))
            mining_sha = persist_table(run, prefix, "negatives", mined, (train["graph_sha"], truth_sha["train"], plan_sha))
            by_key = {(r.s1_id, r.target_id): r for r in train["features"]}
            matrix = feature_matrix(tuple(by_key[p.s1_id, p.target_id] for p in mined))
            with RSSSampler() as sampler:
                scorer, fit_measurement = sampler.measure("fit", lambda definition=definition, matrix=matrix, mined=mined: ResearchScorer(definition).fit(matrix, np.array([p.label for p in mined])))
            fit_seconds = fit_measurement[1]
            models[prefix] = scorer
            model_sha = run.json(f"{prefix}/model.json", scorer.payload, "model-fit", (train["feature_sha"], mining_sha, truth_sha["train"], definition_sha))
            run.json(f"{prefix}/model_identity.json", {"schema_version": "concord.c4.model-identity.v1", "model_sha256": scorer.fingerprint(),
                "training_dataset_fingerprint": dataset_fingerprint(train["records"]), "split_fingerprint": fixture.plan.split_sha256("train"),
                "split_plan_sha256": fixture.plan.sha256, "negative_artifact_sha256": mining_sha, "feature_artifact_sha256": train["feature_sha"],
                "definition_sha256": definition.sha256}, "model-identity", (model_sha, mining_sha, definition_sha))
            summary[prefix] = {"definition_sha256": definition.sha256, "fit_seconds": fit_seconds,
                               "fit_sampled_peak_rss_bytes": fit_measurement[2], "fit_start_rss_bytes": fit_measurement[3],
                               "memory_method": MEMORY_METHOD,
                               "model_fingerprint": scorer.fingerprint(), "negative_count": sum(not p.label for p in mined), "roles": {}}
            for role in ("calibration", "test"):
                prepared = cache[definition.retrieval, role]
                result = execute_resolution(prepared, scorer, selected[role][1], fixture.plan.split_sha256(role), run.manifest["git"]["commit_sha"], fixture.ambiguities if role == "test" else (), population=f"P0/multilingual-c4/{role}")
                result["truth"] = selected[role][1]
                results[prefix, role] = result
                report, entries = persist_resolution(run, f"{prefix}/{role}", prepared, result, truth_sha[role], model_sha, fixture.plan.split_sha256(role))
                summary[prefix]["roles"][role] = report
                if prefix == "reference" and role == "test":
                    seen = Counter()
                    for e in entries:
                        key = e.error_type, e.failure_stage
                        if seen[key] < 2:
                            examples.append(asdict(e))
                            seen[key] += 1
        comparisons = {}
        for name in summary:
            if name == "reference":
                continue
            a, b = results["reference", "test"], results[name, "test"]
            pairs_a = {(f.s1_id, f.target_id, f.error_type): f.failure_stage for f in a["failures"]}
            pairs_b = {(f.s1_id, f.target_id, f.error_type): f.failure_stage for f in b["failures"]}
            movement = Counter(pairs_a.get(k, "NOT_ERROR") + "→" + pairs_b.get(k, "NOT_ERROR") for k in pairs_a.keys() | pairs_b.keys())
            memberships = cohort_members(cache["reference", "test"]["records"], selected["test"][1], cache["reference", "test"]["candidates"], a["scores"], a["owners"])
            arows = {r["s1_id"]: r for r in a["quality"]["per_query"]}
            brows = {r["s1_id"]: r for r in b["quality"]["per_query"]}
            comparisons[name] = {"macro_f05": paired_mean_interval([arows[q]["f05"] for q in sorted(arows)], [brows[q]["f05"] for q in sorted(arows)]),
                "cohort_f05_delta_on_reference_membership": {tag: {"query_count": len(ids), "delta": float(np.mean([brows[q]["f05"] - arows[q]["f05"] for q in ids]))} for tag, ids in memberships.items()},
                "failure_stage_movement": dict(sorted(movement.items())), "promotion": "DIAGNOSTIC_ONLY"}
            comparisons[name]["absolute_metric_deltas"] = {m: b["quality"][m] - a["quality"][m] for m in ("macro_f05", "macro_precision", "macro_recall", "exact_set_accuracy")}
            comparisons[name]["resources"] = {"reference_fit_seconds": summary["reference"]["fit_seconds"], "challenger_fit_seconds": summary[name]["fit_seconds"],
                "reference_fit_sampled_peak_rss_bytes": summary["reference"]["fit_sampled_peak_rss_bytes"],
                "challenger_fit_sampled_peak_rss_bytes": summary[name]["fit_sampled_peak_rss_bytes"],
                "reference_resolution_seconds": a["resolution_seconds"], "challenger_resolution_seconds": b["resolution_seconds"],
                "timing_limitation": "single suite execution, shared process and cached graphs; scale repetitions separately retained"}
            graph = cache[models[name].definition.retrieval, "test"]
            cross_ids = set(memberships.get("cross_script", ()))
            cross_truth = tuple(p for p in selected["test"][1] if p[0] in cross_ids)
            candidate_keys = {(c.s1_id, c.target_id) for c in graph["candidates"]}
            comparisons[name]["retrieval"] = {"candidate_count": len(candidate_keys),
                "candidate_delta": len(candidate_keys) - len(cache["reference", "test"]["candidates"]),
                "overall_truth_recall": graph["retrieval_report"]["truth_pair_recall"],
                "cross_script_truth_count": len(cross_truth),
                "cross_script_truth_recall": sum(p in candidate_keys for p in cross_truth) / len(cross_truth) if cross_truth else None,
                "retrieval_seconds": graph["retrieval_seconds"], "feature_seconds": graph["feature_seconds"]}
        run.json("comparisons.json", comparisons, "paired-comparison", tuple(run.manifest["artifacts"][f"{d.name}/test/result.json"]["sha256"] for d in definitions))
        reference = results["reference", "test"]
        raw_ids, confidence, structure, raw = structure_inputs(reference["capsules"], reference["dispositions"])
        exact = {r["s1_id"]: int(not r["exact_set"]) for r in reference["quality"]["per_query"]}
        study = risk_comparison(raw_ids, [exact[q] for q in raw_ids], confidence, structure)
        study["raw_confidence_diagnostics"] = raw
        study["predeclared_structure_formula"] = "mean(1-lanes/5,1-min(1,ownership_margin),1-min(1,threshold_margin/.36),ambiguity); undefined accepted diagnostics contribute zero before inversion"
        study["confidence_formula"] = "1-minimum accepted score; zero-match uses top rejected score, or 0 when no candidates"
        study["individual_confidence_baselines"] = {}
        for field in ("top_candidate_score", "minimum_accepted_score", "best_rejected_score", "score_gap"):
            indices = [i for i, row in enumerate(raw) if row[field] is not None]
            risks = [raw[i][field] if field == "best_rejected_score" else 1 - raw[i][field] for i in indices]
            study["individual_confidence_baselines"][field] = risk_comparison(tuple(raw_ids[i] for i in indices), [exact[raw_ids[i]] for i in indices], risks, [structure[i] for i in indices]) if indices else None
        study["zero_match_confidence_validation"] = {}
        for tag, nonempty in (("zero_match", False), ("nonempty", True)):
            indices = [i for i, row in enumerate(raw) if (row["minimum_accepted_score"] is not None) == nonempty]
            study["zero_match_confidence_validation"][tag] = risk_comparison(tuple(raw_ids[i] for i in indices), [exact[raw_ids[i]] for i in indices], [confidence[i] for i in indices], [structure[i] for i in indices]) if indices else None
        run.json("stability_vs_confidence.json", study, "risk-coverage-study", (run.manifest["artifacts"]["reference/test/capsules.json"]["sha256"], truth_sha["test"]))
        robustness = {}
        test_records, test_truth = selected["test"]
        original_sets = {d.s1_id: d.accepted_targets for d in reference["decisions"]}
        for name in PERTURBATIONS:
            records = perturb(test_records, name)
            # All pipeline stages, including retrieval and graph features, are rerun.
            split_sha = content_sha256({"parent_split": fixture.plan.split_sha256("test"), "perturbation": name,
                                       "dataset": dataset_fingerprint(records), "recipe": RECIPE_VERSION})
            prepared = prepare(run, records, "perturbation-" + name, "reference", test_truth, root_sha, split_sha)
            result = execute_resolution(prepared, models["reference"], test_truth, split_sha, run.manifest["git"]["commit_sha"], fixture.ambiguities)
            result["truth"] = test_truth
            report, _ = persist_resolution(run, "robustness/" + name, prepared, result, truth_sha["test"], run.manifest["artifacts"]["reference/model.json"]["sha256"], split_sha)
            sets = {d.s1_id: d.accepted_targets for d in result["decisions"]}
            changed = [q for q in sorted(original_sets) if original_sets[q] != sets[q]]
            observations = [asdict(StabilityObservation(q, name, original_sets[q], sets[q])) for q in sorted(original_sets)]
            run.json(f"robustness/{name}/observations.json", observations, "decision-changes", (run.manifest["artifacts"][f"robustness/{name}/resolutions.parquet"]["sha256"], run.manifest["artifacts"]["reference/test/resolutions.parquet"]["sha256"]))
            robustness[name] = {"evaluated_original_query_count": len(original_sets), "changed_count": len(changed), "change_rate": len(changed) / len(original_sets),
                                "changed_queries": changed, "quality": report["quality"], "cohorts": report["cohorts"],
                                "profile": profile(records), "dataset_fingerprint": dataset_fingerprint(records),
                                "candidate_count": report["candidate_count"], "calibration": report["calibration"],
                                "failures": report["failures"], "retrieval": prepared["retrieval_report"]}
        # Actual row-order permutation reruns retrieval/features/inference, not a hash-only check.
        candidates, config, identity, _, _, _ = candidate_graph(tuple(reversed(test_records)), "reference")
        features = generate_features(tuple(normalize(r) for r in reversed(test_records)), candidates, config)
        permuted = dict(cache["reference", "test"], candidates=candidates, features=features, retrieval_sha=identity)
        replay = execute_resolution(permuted, models["reference"], test_truth, fixture.plan.split_sha256("test"), run.manifest["git"]["commit_sha"], fixture.ambiguities)
        if reference["decisions"] != replay["decisions"] or reference["scores"] != replay["scores"]:
            raise ValueError("row permutation changed frozen reference outputs")
        train = cache["reference", "train"]
        mined = mine_negatives(train["records"], train["candidates"], selected["train"][1], fixture.plan, "train", train["retrieval_sha"], train["graph_sha"])
        by_key = {(r.s1_id, r.target_id): r for r in train["features"]}
        repeated = ResearchScorer(definitions[0]).fit(feature_matrix(tuple(by_key[p.s1_id, p.target_id] for p in mined)), np.array([p.label for p in mined]))
        repeated_output = execute_resolution(cache["reference", "test"], repeated, test_truth, fixture.plan.split_sha256("test"), run.manifest["git"]["commit_sha"], fixture.ambiguities)
        if repeated.fingerprint() != models["reference"].fingerprint() or repeated_output["scores"] != reference["scores"]:
            raise ValueError("reference repeat differed on this platform")
        run.json("robustness.json", {"perturbations": robustness, "row_order_identical": True, "same_input_repeat_identical": True,
            "repeated_model_sha256": repeated.fingerprint(),
            "permutation_resolution_sha256": content_sha256([asdict(d) for d in replay["decisions"]]),
            "reference_profile": profile(test_records), "meaning": "decision changes after actual frozen-model pipeline reruns; no capsule stability boolean"}, "robustness-drift", tuple(a["sha256"] for n, a in run.manifest["artifacts"].items() if n.startswith("robustness/") or n == "reference/test/result.json"))
        run.json("failure_atlas_summary.json", {"entry_count": len(reference["failures"]), "counts": reference["failure_report"]["counts"], "examples": examples,
            "bounded_example_policy": "top8 candidates plus attributed pair if retrieved; complete bulk stages retained separately"}, "failure-atlas-summary", (run.manifest["artifacts"]["reference/test/atlas.parquet"]["sha256"],))
        output = {"schema_version": "concord.pass-c-public-summary.v1", "recipe": RECIPE_VERSION,
                  "dataset_fingerprint": dataset_fingerprint(fixture.records), "split_plan_sha256": fixture.plan.sha256,
                  "experiments": summary, "comparisons": comparisons, "robustness": robustness,
                  "stability_vs_confidence": study, "repeat_equal": True, "row_order_equal": True}
        run.json("summary.json", output, "pass-c-summary", tuple(a["sha256"] for a in run.manifest["artifacts"].values()))
        run.complete({"reference_test_macro_f05": reference["quality"]["macro_f05"], "experiment_count": len(definitions), "query_count": len(original_sets)})
        return output
