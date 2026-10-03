"""Executed public scale observations with consistent sampled process RSS."""

import gc
import statistics
import threading
import time
from dataclasses import asdict
from pathlib import Path

import psutil
import pyarrow as pa

from concord.c3_cli import retained_run, verified_run
from concord.features.reference import FEATURE_SCHEMA_SHA256, generate_features
from concord.identity import dataset_fingerprint
from concord.inference.resolution import DecoderConfig, decode, evidence_capsules, global_ownership
from concord.metadata import content_sha256, read_json
from concord.modeling.scorer import score_features
from concord.normalization import normalize
from concord.research.definitions import ExperimentDefinition, ScaleObservation
from concord.research.experiments import persist_table
from concord.research.fixtures import RECIPE_VERSION, workload
from concord.research.scorers import ResearchScorer
from concord.retrieval.baseline import retrieve, synthetic_config
from concord.storage import _write, write_candidates, write_entities, write_normalized

MEMORY_METHOD = "process RSS sampled with psutil every 10ms plus explicit stage start/end; sampled maximum, not OS peak or isolated allocation"
SCALE_SCHEMA = pa.schema([
    pa.field(n, t, False) for n, t in (
        ("query_count", pa.int32()), ("target_count", pa.int32()), ("candidate_count", pa.int64()),
        ("repetition", pa.int32()), ("stage", pa.string()), ("wall_seconds", pa.float64()),
        ("sampled_peak_rss_bytes", pa.int64()), ("start_rss_bytes", pa.int64()), ("samples", pa.int32()))
], metadata={b"concord.schema_version": b"concord.c4.scale-observation.v1"})


class RSSSampler:
    def __enter__(self):
        self.process = psutil.Process()
        self.values = [self.process.memory_info().rss]
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._sample, daemon=True)
        self.thread.start()
        return self

    def _sample(self):
        while not self.stop.wait(.01):
            self.values.append(self.process.memory_info().rss)

    def measure(self, stage, function):
        offset = len(self.values)
        start_rss = self.process.memory_info().rss
        self.values.append(start_rss)
        start = time.perf_counter()
        result = function()
        duration = time.perf_counter() - start
        self.values.append(self.process.memory_info().rss)
        samples = self.values[offset:]
        return result, (stage, duration, max(samples), start_rss, len(samples))

    def __exit__(self, *unused):
        self.stop.set()
        self.thread.join()


def pipeline(records, scorer, split_sha, commit):
    config = synthetic_config()
    with RSSSampler() as sampler:
        first_rss = sampler.values[0]
        start = time.perf_counter()
        normalized, a = sampler.measure("normalization", lambda: tuple(normalize(r) for r in records))
        retrieval, b = sampler.measure("retrieval", lambda: retrieve(normalized, config))
        features, c = sampler.measure("features", lambda: generate_features(normalized, retrieval.candidates, config))
        scores, d = sampler.measure("scoring", lambda: score_features(features, retrieval.candidates, scorer, model_version="concord.c4.numeric-model.v1"))
        owners, e = sampler.measure("ownership", lambda: global_ownership(scores))
        queries = tuple(r.entity_id for r in records if r.source == "S1")
        (dispositions, decisions), f = sampler.measure("decoding", lambda: decode(owners, queries))
        capsules, g = sampler.measure("evidence", lambda: evidence_capsules(retrieval.candidates, scores, owners, dispositions, decisions,
            dataset_sha=dataset_fingerprint(records), split_sha=split_sha, retrieval_sha=config.fingerprint,
            feature_schema_sha=FEATURE_SCHEMA_SHA256, model_sha=scorer.fingerprint(), code_commit=commit))
        duration = time.perf_counter() - start
        sampler.values.append(sampler.process.memory_info().rss)
        total = ("pipeline", duration, max(sampler.values), first_rss, len(sampler.values))
    return {"normalized": normalized, "retrieval": retrieval, "features": features, "scores": scores,
            "ownership": owners, "candidate_dispositions": dispositions, "resolutions": decisions,
            "capsules": capsules}, (a, b, c, d, e, f, g, total)


def run_scale(args):
    sizes = tuple(int(n) for n in args.sizes.split(","))
    if len(sizes) < 2 or tuple(sorted(set(sizes))) != sizes or any(n < 1 or n > 4096 for n in sizes):
        raise ValueError("at least two increasing unique public sizes in 1..4096 required")
    if not 2 <= args.repetitions <= 10 or not 1 <= args.warmups <= 3:
        raise ValueError("scale requires 2..10 measured repetitions and 1..3 warmups")
    parent = verified_run(args.model_run)
    if parent["pipeline_configuration"].get("stage") != "c4-public":
        raise ValueError("scale consumes only a verified public C4 model run")
    model = parent["artifacts"]["reference/model.json"]["sha256"]
    scorer = ResearchScorer.load(read_json(Path(args.model_run) / "reference/model.json"))
    if scorer.definition != ExperimentDefinition("reference"):
        raise ValueError("scale requires the unchanged reference definition")
    records, _ = workload(max(sizes))
    split = content_sha256({"recipe": RECIPE_VERSION, "sizes": sizes, "purpose": "scale, not quality evaluation"})
    config = {"stage": "c4-scale", "recipe": RECIPE_VERSION, "sizes": sizes,
              "repetitions": args.repetitions, "warmups_per_size": args.warmups,
              "retrieval": asdict(synthetic_config()), "decoder": asdict(DecoderConfig()),
              "model_fingerprint": scorer.fingerprint(), "parent_model_artifact": model,
              "memory_method": MEMORY_METHOD, "workers": 1, "model_threads": 1,
              "hardware": {"logical_cpus": psutil.cpu_count(), "physical_cpus": psutil.cpu_count(logical=False),
                           "total_ram_bytes": psutil.virtual_memory().total},
              "timing_scope": "normalization through evidence; excludes imports, fixture generation, model loading, GC, serialization; pipeline includes sampler bookkeeping"}
    with retained_run(args, records, split, config) as run:
        run.copy(Path(args.model_run) / "reference/model.json", "reference_model.json", "model-parent", "concord.c4.numeric-model.v1", (*parent["artifacts"]["reference/model.json"]["lineage"]["parent_sha256"], parent["configuration_fingerprint"]))
        run.json("model_source.json", {"source_experiment_id": parent["experiment_id"],
            "source_git": parent["git"], "source_model_sha256": model,
            "source_model_lineage": parent["artifacts"]["reference/model.json"]["lineage"]}, "model-source", (model, parent["configuration_fingerprint"]))
        observations, summaries = [], {}
        for count in sizes:
            selected, _ = workload(count)
            repeated_sets = []
            local_split = content_sha256({"dataset": dataset_fingerprint(selected), "purpose": "scale", "recipe": RECIPE_VERSION})
            for _ in range(args.warmups):
                gc.collect()
                pipeline(selected, scorer, local_split, run.manifest["git"]["commit_sha"])
            for repetition in range(args.repetitions):
                gc.collect()
                products, measurements = pipeline(selected, scorer, local_split, run.manifest["git"]["commit_sha"])
                candidates = products["retrieval"].candidates
                repeated_sets.append(content_sha256([asdict(d) for d in products["resolutions"]]))
                observations.extend(ScaleObservation(count, len(selected) - count, len(candidates), repetition, *m) for m in measurements)
                if repetition == args.repetitions - 1:
                    prefix = f"size-{count}"
                    write_entities(run.out / f"{prefix}/entities.parquet", selected)
                    entity_sha = run.artifact(f"{prefix}/entities.parquet", "scale-ingest", "concord.entity.v1", (dataset_fingerprint(selected), split))
                    write_normalized(run.out / f"{prefix}/normalized.parquet", products["normalized"])
                    norm_sha = run.artifact(f"{prefix}/normalized.parquet", "normalize", "concord.normalized-entity.v1", (entity_sha,))
                    write_candidates(run.out / f"{prefix}/candidates.parquet", candidates)
                    graph_sha = run.artifact(f"{prefix}/candidates.parquet", "retrieve", "concord.retrieval-candidate.v1", (norm_sha, synthetic_config().fingerprint))
                    previous = graph_sha
                    for stage in ("features", "scores", "ownership", "candidate_dispositions", "resolutions"):
                        parents = (previous, model) if stage == "scores" else (previous, FEATURE_SCHEMA_SHA256, norm_sha) if stage == "features" else (previous, DecoderConfig().sha256) if stage == "candidate_dispositions" else (previous,)
                        previous = persist_table(run, prefix, stage, products[stage], parents)
                    run.json(f"{prefix}/capsules.json", [asdict(c) for c in products["capsules"]], "resolution-evidence", (previous, graph_sha, model, local_split))
                    run.json(f"{prefix}/retrieval_fit.json", {"fit_evidence": [asdict(f) for f in products["retrieval"].fit_evidence], "warnings": products["retrieval"].warnings}, "retrieval-fit", (graph_sha, norm_sha))
                else:
                    del products
            if len(set(repeated_sets)) != 1:
                raise ValueError("scale repetitions changed logical resolution sets")
            rows = [o for o in observations if o.query_count == count]
            summaries[str(count)] = {"query_count": count, "target_count": rows[0].target_count,
                "candidate_count": rows[0].candidate_count, "dataset_fingerprint": dataset_fingerprint(selected),
                "resolution_fingerprint": repeated_sets[0], "repeat_resolution_fingerprints": repeated_sets,
                "stages": {stage: {"median_seconds": statistics.median([r.wall_seconds for r in rows if r.stage == stage]),
                    "range_seconds": [min(r.wall_seconds for r in rows if r.stage == stage), max(r.wall_seconds for r in rows if r.stage == stage)],
                    "maximum_sampled_rss_bytes": max(r.sampled_peak_rss_bytes for r in rows if r.stage == stage),
                    "median_queries_per_second": count / statistics.median([r.wall_seconds for r in rows if r.stage == stage]),
                    "median_candidates_per_second": rows[0].candidate_count / statistics.median([r.wall_seconds for r in rows if r.stage == stage])} for stage in sorted({r.stage for r in rows})},
                "retained_stage_bytes": sum(a["bytes"] for name, a in run.manifest["artifacts"].items() if name.startswith(f"size-{count}/"))}
            del products
        _write(run.out / "observations.parquet", [asdict(o) for o in observations], SCALE_SCHEMA)
        run.artifact("observations.parquet", "scale-measurement", "concord.c4.scale-observation.v1", tuple(a["sha256"] for a in run.manifest["artifacts"].values()))
        output = {"schema_version": "concord.c4.scale-summary.v1", "workloads": summaries, "configuration": config,
                  "environment": run.manifest["operational"]["environment"], "warning": "Current invented public workloads only; no production/historical-scale or controlled cross-platform speed claim."}
        run.json("summary.json", output, "scale-summary", tuple(a["sha256"] for a in run.manifest["artifacts"].values()))
        run.complete({"workload_count": len(sizes), "observation_count": len(observations)})
        return output
