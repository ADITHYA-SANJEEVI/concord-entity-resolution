"""C3 orchestration over verified C2 artifacts; no retrieval implementation here."""

import shutil
import time
from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import numpy as np
import psutil

from concord.c3_storage import DEFINITIONS, read_stage, write_stage
from concord.cli import _environment, _git, _record_failed_manifest, _truth
from concord.evaluation.failures import attribute_failures, failure_report
from concord.evaluation.quality import calibration_report, quality_report
from concord.features.reference import REFERENCE_SCHEMA, feature_matrix, generate_features
from concord.identity import dataset_fingerprint
from concord.inference.resolution import DecoderConfig, decode, evidence_capsules, global_ownership
from concord.metadata import (
    ArtifactLineage,
    content_sha256,
    lineage_dict,
    read_json,
    validate_manifest,
    write_json,
)
from concord.modeling.scorer import LightGBMScorer, ModelConfig, model_metadata, score_features
from concord.modeling.training import NegativeConfig, load_plan, mine_negatives
from concord.normalization import normalize
from concord.provenance import sha256_file
from concord.retrieval.analysis import candidate_fingerprint, evaluate_retrieval
from concord.retrieval.baseline import RetrievalConfig, process_peak_rss
from concord.storage import read_candidates, read_entities, read_normalized


def verified_run(directory: str | Path) -> dict:
    root = Path(directory)
    manifest = read_json(root / "manifest.json")
    validate_manifest(manifest)
    if manifest["disposition"] != "COMPLETED":
        raise ValueError("only validated COMPLETED runs can be consumed")
    for name, item in manifest["artifacts"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or sha256_file(path) != item["sha256"]:
            raise ValueError("artifact path/hash mismatch")
        if path.stat().st_size != item["bytes"]:
            raise ValueError("artifact size mismatch")
    return manifest


def _identity(directory, manifest, name):
    if name not in manifest["artifacts"]:
        raise ValueError(f"required parent artifact absent: {name}")
    return manifest["artifacts"][name]["sha256"]


class Run:
    def __init__(self, args, records, split_sha, configuration):
        self.out = Path(args.output)
        if self.out.exists() and any(self.out.iterdir()):
            raise ValueError("output directory must be new or empty; previous evidence is retained")
        self.out.mkdir(parents=True, exist_ok=True)
        environment = _environment()
        environment["packages"].update({name: version(name) for name in ("lightgbm", "RapidFuzz", "Unidecode")})
        self.manifest = {
            "schema_version": "concord.experiment.v1", "experiment_id": args.run_id,
            "timestamp_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"), "git": _git(),
            "provenance": {"dataset_fingerprint": dataset_fingerprint(records), "split_fingerprint": split_sha,
                           "dataset_track": args.track, "population": args.population},
            "pipeline_configuration": configuration, "configuration_fingerprint": content_sha256(configuration),
            "operational": {"environment": environment}, "artifacts": {}, "metrics": {},
            "evidence": {"class": "D", "notes": []}, "disposition": "RUNNING", "promotion": "DIAGNOSTIC_ONLY",
        }
        self.start, self.cpu = time.perf_counter(), time.process_time()
        validate_manifest(self.manifest)
        write_json(self.out / "manifest.json", self.manifest)

    def artifact(self, name, stage, schema, parents):
        digest = sha256_file(self.out / name)
        lineage = ArtifactLineage(digest, tuple(dict.fromkeys(parents)),
                                  self.manifest["configuration_fingerprint"], self.manifest["git"]["commit_sha"],
                                  schema, stage, "D")
        self.manifest["artifacts"][name] = {"sha256": digest, "bytes": (self.out / name).stat().st_size,
                                             "lineage": lineage_dict(lineage)}
        return digest

    def json(self, name, value, stage, parents=()):
        write_json(self.out / name, value)
        schema = value.get("schema_version", "concord.c3-metadata.v1") if isinstance(value, dict) else "concord.c3-records.v1"
        return self.artifact(name, stage, schema, parents)

    def table(self, stage, rows, parents):
        name = f"{stage}.parquet"
        write_stage(self.out / name, stage, rows)
        return self.artifact(name, stage, DEFINITIONS[stage][1], parents)

    def copy(self, source, name, stage, schema, parents):
        shutil.copyfile(source, self.out / name)
        return self.artifact(name, stage, schema, parents)

    def complete(self, report):
        def collect(value, path=""):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == "negative_policy":
                        continue  # configuration is retained, not presented as a measured metric
                    collect(child, f"{path}.{key}" if path else key)
            elif value is None or type(value) in (int, float):
                unit = "count" if any(w in path for w in ("count", ".tp", ".fp", ".fn")) else "fraction"
                if "log_loss" in path:
                    unit = "nats"
                self.manifest["metrics"][path] = {"name": path, "value": value, "unit": unit,
                    "population": self.manifest["provenance"]["population"], "evidence_class": "D",
                    "producing_run": self.manifest["experiment_id"]}
        collect(report)
        self.manifest["operational"].update({
            "wall_seconds": time.perf_counter() - self.start, "cpu_seconds": time.process_time() - self.cpu,
            "peak_process_rss_bytes": process_peak_rss(), "sampled_peak_rss_bytes": psutil.Process().memory_info().rss,
            "rss_semantics": "process-lifetime peak; end-of-run sampled RSS; tiny smoke observation",
            "artifact_bytes_written": sum(a["bytes"] for a in self.manifest["artifacts"].values()),
        })
        self.manifest["disposition"] = "COMPLETED"
        validate_manifest(self.manifest)
        write_json(self.out / "manifest.json", self.manifest)


@contextmanager
def retained_run(args, records, split_sha, config):
    run = Run(args, records, split_sha, config)
    try:
        yield run
    except Exception as error:
        _record_failed_manifest(run.out, run.manifest, error)
        raise


def _inputs(args):
    records = read_entities(args.entities)
    plan = load_plan(read_json(args.split_plan))
    selected = plan.select(records, args.split)
    root = Path(args.retrieval_run)
    manifest = verified_run(root)
    if manifest["provenance"]["dataset_fingerprint"] != dataset_fingerprint(selected):
        raise ValueError("retrieval run does not match the declared split records")
    if read_entities(root / "entities.parquet") != selected:
        raise ValueError("retrieval entity artifact differs from split membership")
    normalized = read_normalized(root / "normalized_entities.parquet")
    if normalized != tuple(normalize(r) for r in selected):
        raise ValueError("retrieval normalization does not match declared records")
    candidates = read_candidates(root / "retrieval_candidates.parquet")
    freeze = read_json(root / "retrieval_freeze.json")
    values = dict(manifest["pipeline_configuration"]["retrieval"])
    values["lanes"], values["budgets"] = tuple(values["lanes"]), tuple(values["budgets"])
    config = RetrievalConfig(**values)
    if freeze["configuration_fingerprint"] != config.fingerprint or freeze["candidate_fingerprint"] != candidate_fingerprint(candidates):
        raise ValueError("retrieval freeze/config/graph mismatch")
    evaluate_retrieval(selected, candidates)
    return records, selected, plan, root, manifest, normalized, candidates, config


def _graph_artifacts(run, records, plan, split_name, root, parent, config):
    context = {"schema_version": "concord.c3-context.v1", "split_name": split_name,
               "split_role": plan.group(split_name).role, "full_dataset_fingerprint": plan.dataset_fingerprint,
               "dataset_fingerprint": dataset_fingerprint(records), "split_fingerprint": plan.split_sha256(split_name),
               "split_plan_sha256": plan.sha256, "retrieval_configuration": asdict(config),
               "retrieval_config_sha256": config.fingerprint, "feature_schema_sha256": REFERENCE_SCHEMA.sha256}
    plan_sha = run.json("split_plan.json", asdict(plan), "split-policy", (plan.dataset_fingerprint,))
    context_sha = run.json("context.json", context, "split-context", (plan_sha,))
    entity_sha = run.copy(root / "entities.parquet", "entities.parquet", "ingest", "concord.entity.v1", (dataset_fingerprint(records),))
    normalized_sha = run.copy(root / "normalized_entities.parquet", "normalized_entities.parquet", "normalize", "concord.normalized-entity.v1", (entity_sha,))
    freeze_sha = run.copy(root / "retrieval_freeze.json", "retrieval_freeze.json", "retrieve-freeze", "concord.retrieval-freeze.v1",
                         (_identity(root, parent, "retrieval_candidates.parquet"),))
    candidate_sha = run.copy(root / "retrieval_candidates.parquet", "retrieval_candidates.parquet", "retrieve", "concord.retrieval-candidate.v1",
                            (normalized_sha, config.fingerprint))
    schema_sha = run.json("feature_schema.json", asdict(REFERENCE_SCHEMA), "feature-schema", (REFERENCE_SCHEMA.sha256,))
    return context, context_sha, normalized_sha, candidate_sha, freeze_sha, schema_sha


def train_command(args):
    if args.action == "fingerprint":
        root = Path(args.model_run)
        verified_run(root)
        metadata = read_json(root / "model_metadata.json")
        LightGBMScorer.load(root / "model.txt", metadata)
        return metadata
    if args.action == "calibrate":
        args.action = "calibration"
        return evaluate_command(args)
    _, records, plan, root, parent, normalized, candidates, retrieval = _inputs(args)
    if plan.group(args.split).role != "train":
        raise ValueError("train commands require explicit training membership")
    negatives = NegativeConfig(**read_json(args.negative_config)) if args.negative_config else NegativeConfig()
    model_config = ModelConfig(**read_json(args.model_config)) if args.model_config else ModelConfig()
    config = {"stage": "train", "action": args.action, "split_plan_sha256": plan.sha256,
              "retrieval": asdict(retrieval), "negative_mining": asdict(negatives), "model": asdict(model_config),
              "feature_schema_sha256": REFERENCE_SCHEMA.sha256}
    with retained_run(args, records, plan.split_sha256(args.split), config) as run:
        _, context_sha, normalized_sha, graph_sha, freeze_sha, schema_sha = _graph_artifacts(run, records, plan, args.split, root, parent, retrieval)
        truth = _truth(args.truth)
        if truth is None:
            raise ValueError("explicit training truth required")
        mined = mine_negatives(records, candidates, truth, plan, args.split, retrieval.fingerprint, graph_sha, negatives)
        truth_sha = run.json("training_truth.json", sorted(truth), "training-labels", (context_sha,))
        mined_sha = run.table("negatives", mined, (graph_sha, truth_sha, context_sha, negatives.sha256))
        features = generate_features(normalized, candidates, retrieval)
        feature_sha = run.table("features", features, (graph_sha, normalized_sha, freeze_sha, schema_sha))
        report = {"population": args.population, "split_role": "train", "positive_count": sum(p.label for p in mined),
                  "negative_count": sum(not p.label for p in mined), "candidate_count": len(candidates),
                  "retrieved_truth_count": sum(p.label for p in mined), "truth_count": len(truth),
                  "unretrieved_truth_count": len(truth) - sum(p.label for p in mined),
                  "negative_policy": asdict(negatives), "feature_schema_sha256": REFERENCE_SCHEMA.sha256}
        report_parents = [mined_sha, feature_sha]
        if args.action == "fit":
            by_key = {(r.s1_id, r.target_id): r for r in features}
            training = tuple(by_key[p.s1_id, p.target_id] for p in mined)
            scorer = LightGBMScorer(model_config).fit(feature_matrix(training), np.array([p.label for p in mined]))
            scorer.save(run.out / "model.txt")
            model_sha = run.artifact("model.txt", "model-fit", "concord.lightgbm-text.v1", (feature_sha, mined_sha, truth_sha, model_config.sha256))
            metadata = model_metadata(scorer, dataset_fingerprint(records), plan.split_sha256(args.split), plan.sha256,
                                      negatives.sha256, content_sha256([asdict(p) for p in mined]), feature_sha, retrieval.fingerprint)
            metadata_sha = run.json("model_metadata.json", metadata, "model-identity", (model_sha, mined_sha, schema_sha))
            report_parents.extend((model_sha, metadata_sha))
            report.update({"model_sha256": model_sha, "model_identity_sha256": metadata["model_identity_sha256"],
                           "actual_tree_count": metadata["actual_tree_count"]})
        run.json("report.json", report, "training-report", tuple(report_parents))
        run.complete(report)
        return report


def resolve_command(args):
    if args.action in ("explain", "export-evidence"):
        root = Path(args.resolution_run)
        verified_run(root)
        records = read_json(root / "resolution_evidence.json")
        if args.action == "export-evidence":
            return {"evidence": records}
        found = [r for r in records if r["s1_id"] == args.s1_id]
        if not found:
            raise ValueError("unknown query in evidence")
        dispositions = read_stage(root / "candidate_dispositions.parquet", "candidate_dispositions")
        rejected = sorted((d for d in dispositions if d.s1_id == args.s1_id and not d.accepted), key=lambda d: (-d.score, d.target_id))
        candidates = {(r.s1_id, r.target_id): r for r in read_candidates(root / "retrieval_candidates.parquet")}
        ownership = {(r.s1_id, r.target_id): r for r in read_stage(root / "ownership.parquet", "ownership")}
        return {"evidence": found[0], "top_rejected": [{"disposition": asdict(d),
                "retrieval": asdict(candidates[d.s1_id, d.target_id]), "ownership": asdict(ownership[d.s1_id, d.target_id])}
                for d in rejected[:5]],
                "meaning": "Recorded policy evidence, not causal explanation or stability proof"}
    all_records, records, plan, root, parent, normalized, candidates, retrieval = _inputs(args)
    model_root = Path(args.model_run)
    model_manifest = verified_run(model_root)
    metadata = read_json(model_root / "model_metadata.json")
    training_name = next(g.name for g in plan.groups if g.role == "train")
    if (model_manifest["pipeline_configuration"].get("stage") != "train"
            or model_manifest["pipeline_configuration"].get("action") != "fit"
            or metadata["dataset_fingerprint"] != dataset_fingerprint(plan.select(all_records, training_name))):
        raise ValueError("model must originate from the declared training population")
    if (metadata["split_plan_sha256"] != plan.sha256 or metadata["retrieval_config_sha256"] != retrieval.fingerprint
            or metadata["split_fingerprint"] != plan.split_sha256(training_name)):
        raise ValueError("model split/retrieval provenance mismatch")
    if model_manifest["provenance"]["dataset_fingerprint"] != metadata["dataset_fingerprint"]:
        raise ValueError("model training dataset mismatch")
    scorer = LightGBMScorer.load(model_root / "model.txt", metadata)
    decoder = DecoderConfig()
    config = {"stage": "resolve", "retrieval": asdict(retrieval), "decoder": asdict(decoder),
              "model_identity_sha256": metadata["model_identity_sha256"], "split_plan_sha256": plan.sha256,
              "feature_schema_sha256": REFERENCE_SCHEMA.sha256}
    with retained_run(args, records, plan.split_sha256(args.split), config) as run:
        context, context_sha, normalized_sha, graph_sha, freeze_sha, schema_sha = _graph_artifacts(run, records, plan, args.split, root, parent, retrieval)
        features = generate_features(normalized, candidates, retrieval)
        feature_sha = run.table("features", features, (graph_sha, normalized_sha, freeze_sha, schema_sha))
        scores = score_features(features, candidates, scorer)
        model_identity = _identity(model_root, model_manifest, "model_metadata.json")
        score_sha = run.table("scores", scores, (feature_sha, metadata["model_sha256"], model_identity))
        ownership = global_ownership(scores)
        owner_sha = run.table("ownership", ownership, (score_sha, content_sha256({"ownership_policy": decoder.ownership_policy})))
        queries = tuple(r.entity_id for r in records if r.source == "S1")
        dispositions, decisions = decode(ownership, queries, decoder)
        disposition_sha = run.table("candidate_dispositions", dispositions, (owner_sha, score_sha, decoder.sha256))
        resolution_sha = run.table("resolutions", decisions, (disposition_sha, context_sha))
        capsules = evidence_capsules(candidates, scores, ownership, dispositions, decisions,
            dataset_sha=context["dataset_fingerprint"], split_sha=context["split_fingerprint"],
            retrieval_sha=retrieval.fingerprint, feature_schema_sha=REFERENCE_SCHEMA.sha256,
            model_sha=metadata["model_sha256"], code_commit=run.manifest["git"]["commit_sha"])
        run.json("resolution_evidence.json", [asdict(r) for r in capsules], "resolution-evidence",
                 (resolution_sha, score_sha, owner_sha, graph_sha, schema_sha, model_identity, context_sha))
        report = {"population": args.population, "split_role": context["split_role"], "candidate_count": len(candidates),
                  "accepted_link_count": sum(d.accepted for d in dispositions), "query_count": len(queries),
                  "decision_counts": dict(Counter(d.decision_type for d in decisions)),
                  "retrieval_config_sha256": retrieval.fingerprint, "candidate_fingerprint": candidate_fingerprint(candidates),
                  "feature_schema_sha256": REFERENCE_SCHEMA.sha256, "model_sha256": metadata["model_sha256"],
                  "decoder_config_sha256": decoder.sha256, "resolution_fingerprint": content_sha256([asdict(d) for d in decisions]),
                  "scored_predictions_fingerprint": content_sha256([[s.s1_id, s.target_id, s.target_source, s.score] for s in scores])}
        run.json("report.json", report, "resolution-report", (resolution_sha, score_sha))
        run.complete(report)
        return report


def evaluate_command(args):
    root = Path(args.resolution_run)
    parent = verified_run(root)
    context = read_json(root / "context.json")
    if context["split_role"] not in ("calibration", "test"):
        raise ValueError("independent evaluation requires declared held-out membership")
    records = read_entities(root / "entities.parquet")
    candidates = read_candidates(root / "retrieval_candidates.parquet")
    scores, ownership, dispositions, decisions = (read_stage(root / f"{stage}.parquet", stage)
        for stage in ("scores", "ownership", "candidate_dispositions", "resolutions"))
    queries = tuple(r.entity_id for r in records if r.source == "S1")
    config = {"stage": "evaluate", "action": args.action, "resolution_artifact_sha256": _identity(root, parent, "resolutions.parquet"),
              "decoder": asdict(DecoderConfig()), "split_plan_sha256": context["split_plan_sha256"]}
    with retained_run(args, records, context["split_fingerprint"], config) as run:
        truth = _truth(args.truth)
        if truth is None:
            raise ValueError("explicit held-out truth required")
        evaluate_retrieval(records, candidates, truth)
        truth_sha = run.json("evaluation_truth.json", sorted(truth), "evaluation-labels", (context["split_fingerprint"],))
        quality = quality_report(queries, truth, decisions, args.population)
        labels = set(truth)
        calibration = calibration_report(tuple(int((s.s1_id, s.target_id) in labels) for s in scores),
                                         tuple(s.score for s in scores), args.population + "/retrieved-pairs")
        ambiguous = tuple(tuple(v) for v in read_json(args.ambiguities)) if args.ambiguities else ()
        if any((q, t) not in labels for q, t, _ in ambiguous):
            raise ValueError("ambiguity annotations must refer to declared labelled pairs")
        ambiguity_sha = run.json("ambiguities.json", list(ambiguous), "label-ambiguity", (truth_sha,))
        failures = attribute_failures(queries, truth, candidates, scores, ownership, dispositions, decisions, ambiguous)
        failure_sha = run.table("failure_attribution", failures, (truth_sha, ambiguity_sha,
            *(_identity(root, parent, f"{stage}.parquet") for stage in
              ("retrieval_candidates", "scores", "ownership", "candidate_dispositions", "resolutions"))))
        failure_summary = failure_report(failures, args.population)
        expected_dispositions, expected_decisions = decode(ownership, queries)
        if expected_dispositions != dispositions or expected_decisions != decisions:
            raise ValueError("recorded output violates frozen reference decoder")
        policy = {"threshold": .640, "population": args.population, "ownership_exclusive": True,
                  "accepted_iff_owner_and_admissible": True, "additional_set_policy": None,
                  "target_contention_count": sum(n > 1 for n in Counter(o.target_id for o in ownership).values()),
                  "owner_count": sum(o.is_owner for o in ownership),
                  "ownership_loss_truth_count": failure_summary["counts"]["FALSE_NEGATIVE"]["OWNERSHIP"]}
        run.json("quality.json", quality, "set-quality", (_identity(root, parent, "resolutions.parquet"), truth_sha))
        run.json("calibration.json", calibration, "calibration", (_identity(root, parent, "scores.parquet"), truth_sha))
        run.json("failures.json", failure_summary, "failure-report", (failure_sha,))
        run.json("policy.json", policy, "policy-check", (_identity(root, parent, "ownership.parquet"),
                 _identity(root, parent, "candidate_dispositions.parquet"), truth_sha))
        report = {"population": args.population, "split_role": context["split_role"], "quality": quality,
                  "calibration": calibration, "failures": failure_summary, "policy": policy}
        run.json("report.json", report, "evaluation-report", tuple(a["sha256"] for a in run.manifest["artifacts"].values()))
        run.complete(report)
        return report[args.action] if args.action in report else report


def add_parsers(verbs):
    for verb, actions in (("train", ("fit", "negatives", "calibrate", "fingerprint")),
                          ("resolve", ("run", "explain", "export-evidence")),
                          ("evaluate", ("quality", "calibration", "failures", "policy"))):
        sub = verbs.add_parser(verb).add_subparsers(dest="action", required=True)
        for action in actions:
            command = sub.add_parser(action)
            metadata_only = action in ("fingerprint", "explain", "export-evidence")
            evaluation = verb == "evaluate" or action == "calibrate"
            if verb == "train" and action == "fingerprint" or verb == "resolve" and action == "run":
                command.add_argument("--model-run", required=True)
            if evaluation or verb == "resolve" and action in ("explain", "export-evidence"):
                command.add_argument("--resolution-run", required=True)
            if action == "explain":
                command.add_argument("--s1-id", required=True)
            if metadata_only:
                continue
            if not evaluation:
                for flag in ("entities", "split-plan", "split", "retrieval-run"):
                    command.add_argument(f"--{flag}", required=True)
            if verb == "train" and not evaluation:
                command.add_argument("--truth", required=True)
                command.add_argument("--negative-config")
                command.add_argument("--model-config")
            if evaluation:
                command.add_argument("--truth", required=True)
                command.add_argument("--ambiguities")
            for flag in ("output", "population", "run-id"):
                command.add_argument(f"--{flag}", required=True)
            command.add_argument("--track", choices=("SYNTHETIC_PUBLIC", "PUBLIC", "PRIVATE_LOCAL"), required=True)


def command(args):
    return {"train": train_command, "resolve": resolve_command, "evaluate": evaluate_command}[args.verb](args)
