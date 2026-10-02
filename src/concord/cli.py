"""Pass A CLI: inspect and retrieve. No speculative later-stage commands."""

import argparse
import platform
import subprocess
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import psutil

from concord.contracts import ENTITY_VERSION
from concord.identity import canonical_records, dataset_fingerprint, split_fingerprint
from concord.inspection import profile
from concord.metadata import (
    ArtifactLineage,
    canonical_json,
    content_sha256,
    lineage_dict,
    read_json,
    validate_manifest,
    write_json,
)
from concord.normalization import NORMALIZATION_VERSION, normalize
from concord.provenance import sha256_file
from concord.retrieval.analysis import candidate_fingerprint, evaluate_retrieval, frontier
from concord.retrieval.baseline import RetrievalConfig, retrieve, synthetic_config
from concord.storage import (
    ENTITY_SCHEMA,
    read_entities,
    read_fixture_tsv,
    write_candidates,
    write_entities,
    write_normalized,
)


def _inputs(args) -> tuple:
    sources = [getattr(args, f"source{i}") for i in (1, 2, 3)]
    if args.entities:
        if any(sources):
            raise ValueError("use entities Parquet or source TSV adapters, not both")
        return read_entities(args.entities)
    if not any(sources):
        raise ValueError("provide --entities or explicit --source1/2/3 fixture adapters")
    return canonical_records(r for i, path in enumerate(sources, 1) if path
                             for r in read_fixture_tsv(path, f"S{i}"))


def _configuration(args) -> RetrievalConfig:
    if args.config:
        config = read_json(args.config)
        if not isinstance(config, dict):
            raise ValueError("retrieval config must be a JSON object")
        config = dict(config)
        for key in ("lanes", "budgets"):
            if key in config:
                config[key] = tuple(config[key])
        return RetrievalConfig(**config)
    return synthetic_config() if args.profile == "synthetic" else RetrievalConfig()


def _truth(path: str | None) -> tuple[tuple[str, str], ...] | None:
    if path is None:
        return None
    value = read_json(path)
    if (not isinstance(value, list)
            or any(not isinstance(pair, list) or len(pair) != 2
                   or any(not isinstance(i, str) or not i.strip() for i in pair) for pair in value)):
        raise ValueError("truth JSON must be a list of [s1_id,target_id] pairs")
    return tuple(tuple(pair) for pair in value)


def _git() -> dict:
    root = Path(__file__).resolve().parents[2]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True))
    return {"commit_sha": commit, "dirty": dirty}


def _environment() -> dict:
    packages = ("numpy", "scipy", "scikit-learn", "sparse-dot-topn", "pyarrow", "psutil",
                "jsonschema", "matplotlib")
    package = Path(__file__).resolve().parent
    source_hashes = {path.relative_to(package).as_posix(): sha256_file(path)
                     for path in sorted(package.rglob("*"))
                     if path.suffix in (".py", ".json") and "legacy_amazon" not in path.parts}
    return {"python": platform.python_version(), "os": platform.platform(),
            "cpu": platform.processor() or platform.machine(),
            "available_ram_bytes": psutil.virtual_memory().available,
            "packages": {name: version(name) for name in packages},
            "implementation_source_sha256": source_hashes}


def _metrics(report: dict, run_id: str, population: str) -> dict:
    result = {}

    def collect(value: object, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                collect(item, f"{path}.{key}" if path else key)
        elif value is None or type(value) in (float, int):
            fraction = any(s in path for s in ("recall", "ratio", "rate"))
            unit = "fraction" if fraction else "count"
            if "per_million_added_candidates" in path:
                unit = "recall_fraction_per_million_candidate_pairs"
            elif path == "candidates_per_recovered_truth":
                unit = "candidate_pairs_per_recovered_truth"
            elif path.startswith("density."):
                unit = "candidate_pairs_per_query"
            result[path] = {"name": path, "value": value, "population": population,
                            "unit": unit,
                            "evidence_class": "D", "producing_run": run_id}

    collect(report, "")
    return result


def _retrieve_command(args) -> dict:
    records = _inputs(args)
    config = _configuration(args)
    out = Path(args.output)
    if out.exists() and any(out.iterdir()):
        raise ValueError("output directory must be new or empty; previous runs are retained")
    out.mkdir(parents=True, exist_ok=True)
    configuration = {"normalization_version": NORMALIZATION_VERSION,
                     "retrieval": asdict(config), "command": args.action,
                     "frontier_ks": args.ks if args.action == "frontier" else None}
    dataset_sha = dataset_fingerprint(records)
    split_sha = split_fingerprint(dataset_sha, args.population, "retrieval-evaluation",
                                  ((r.source, r.entity_id) for r in records if r.source == "S1"))
    manifest = {
        "schema_version": "concord.experiment.v1", "experiment_id": args.run_id,
        "timestamp_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "git": _git(), "provenance": {"dataset_fingerprint": dataset_sha,
                                       "split_fingerprint": split_sha,
                                       "dataset_track": args.track, "population": args.population},
        "configuration_fingerprint": content_sha256(configuration),
        "pipeline_configuration": configuration, "metrics": {},
        "operational": {"environment": _environment()}, "artifacts": {},
        "evidence": {"class": "D", "notes": []}, "disposition": "RUNNING",
        "promotion": "DIAGNOSTIC_ONLY",
    }
    validate_manifest(manifest)
    write_json(out / "manifest.json", manifest)

    def artifact(name: str, stage: str, schema: str, parents: tuple[str, ...],
                 producing_config: str | None = None) -> str:
        digest = sha256_file(out / name)
        lineage = ArtifactLineage(digest, parents,
                                  producing_config or manifest["configuration_fingerprint"],
                                  manifest["git"]["commit_sha"], schema, stage, "D")
        manifest["artifacts"][name] = {"sha256": digest, "bytes": (out / name).stat().st_size,
                                        "lineage": lineage_dict(lineage)}
        return digest

    try:
        write_entities(out / "entities.parquet", records)
        entity_sha = artifact("entities.parquet", "ingest", ENTITY_VERSION, (dataset_sha,))
        normalized = tuple(normalize(r) for r in records)
        write_normalized(out / "normalized_entities.parquet", normalized)
        normalized_sha = artifact("normalized_entities.parquet", "normalize",
                                  "concord.normalized-entity.v1", (entity_sha,))
        run = retrieve(normalized, config)
        write_candidates(out / "retrieval_candidates.parquet", run.candidates)
        candidate_sha = artifact("retrieval_candidates.parquet", "retrieve",
                                 "concord.retrieval-candidate.v1", (normalized_sha,))
        freeze = {"schema_version": "concord.retrieval-freeze.v1", "labels_accessed": False,
                  "candidate_fingerprint": candidate_fingerprint(run.candidates),
                  "candidate_artifact_sha256": candidate_sha,
                  "configuration_fingerprint": config.fingerprint,
                  "fit_evidence": [asdict(e) for e in run.fit_evidence],
                  "warnings": run.warnings, "candidate_pair_bound": run.candidate_pair_bound}
        write_json(out / "retrieval_freeze.json", freeze)
        freeze_sha = artifact("retrieval_freeze.json", "retrieve-freeze",
                              "concord.retrieval-freeze.v1", (candidate_sha,))
        # Truth is read only after the baseline graph and provenance are frozen.
        truth = _truth(args.truth)
        truth_sha = None
        if truth is not None:
            write_json(out / "truth.json", sorted(truth))
            truth_sha = artifact("truth.json", "evaluation-labels", "concord.truth-pairs.v1", ())
        report = evaluate_retrieval(records, run.candidates, truth)
        report.update({"schema_version": "concord.retrieval-report.v1",
                       "producing_run": args.run_id, "evidence_class": "D",
                       "population": args.population, "dataset_track": args.track,
                       "dataset_fingerprint": dataset_sha, "split_fingerprint": split_sha,
                       "configuration_fingerprint": config.fingerprint,
                       "candidate_fingerprint": freeze["candidate_fingerprint"],
                       "candidate_pair_bound": run.candidate_pair_bound,
                       "warnings": run.warnings})
        analysis_parents = []
        if args.action == "frontier":
            if truth is None:
                raise ValueError("frontier requires declared truth labels")
            budgets = tuple(int(k) for k in args.ks.split(","))
            runs = []
            for index, k in enumerate(budgets):
                values = asdict(config)
                values["budgets"], values["lanes"] = (k,) * 5, config.lanes
                if config.profile == "historical-five-view-v1":
                    values["profile"] = "historical-budget-variant-v1"
                variant = RetrievalConfig(**values)
                vrun = retrieve(normalized, variant)
                filename = f"frontier_{index}_candidates.parquet"
                write_candidates(out / filename, vrun.candidates)
                analysis_parents.append(artifact(
                    filename, "retrieve-frontier", "concord.retrieval-candidate.v1",
                    (normalized_sha,), variant.fingerprint))
                runs.append(vrun)
            report["frontier"] = frontier(records, tuple(runs), truth)
            from concord.retrieval.plotting import plot_frontier

            plot_frontier(report["frontier"], args.population, out / "frontier.svg")
            analysis_parents.append(artifact(
                "frontier.svg", "retrieval-frontier-plot", "concord.retrieval-frontier.v1",
                tuple(dict.fromkeys(analysis_parents))))
        write_json(out / "report.json", report)
        parents = (candidate_sha, freeze_sha) + ((truth_sha,) if truth_sha else ())
        artifact("report.json", "retrieval-evaluation", "concord.retrieval-report.v1",
                 tuple(dict.fromkeys(parents + tuple(analysis_parents))))
        manifest["metrics"] = _metrics(report, args.run_id, args.population)
        manifest["operational"].update({
            "wall_seconds": run.wall_seconds, "cpu_seconds": run.cpu_seconds,
            "sampled_peak_rss_bytes": run.sampled_peak_rss_bytes,
            "peak_process_rss_bytes": run.peak_process_rss_bytes,
            "rss_semantics": "actual process-lifetime high-water and sampled RSS; "
                             "not isolated stage memory",
            "bytes_read": sum(Path(p).stat().st_size for p in
                              [args.entities, args.source1, args.source2, args.source3, args.truth]
                              if p),
            "artifact_bytes_written": sum(a["bytes"] for a in manifest["artifacts"].values()),
        })
        manifest["evidence"]["notes"] = list(run.warnings)
        manifest["disposition"] = "COMPLETED"
        validate_manifest(manifest)
        write_json(out / "manifest.json", manifest)
        return report
    except Exception as exc:
        manifest["disposition"] = "FAILED"
        manifest["evidence"]["notes"].append(f"{type(exc).__name__}: {exc}")
        write_json(out / "manifest.json", manifest)
        raise


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="concord")
    verbs = p.add_subparsers(dest="verb", required=True)
    for verb, actions in (("inspect", ("profile", "schema", "fingerprint")),
                          ("retrieve", ("run", "frontier", "lane-rescue", "ablate"))):
        sub = verbs.add_parser(verb).add_subparsers(dest="action", required=True)
        for action in actions:
            command = sub.add_parser(action)
            command.add_argument("--entities", help="typed Concord entities Parquet")
            for i in (1, 2, 3):
                command.add_argument(f"--source{i}", help=f"external synthetic TSV, explicit S{i}")
            if verb == "inspect":
                command.add_argument("--split-json", help="split name/purpose/members/cohort_metadata")
            else:
                command.add_argument("--output", required=True)
                command.add_argument("--truth", help="JSON array of [s1_id,target_id] truth pairs")
                command.add_argument("--profile", choices=("historical", "synthetic"),
                                     default="historical")
                command.add_argument("--config", help="explicit immutable retrieval config JSON")
                command.add_argument("--population", required=True, help="exact split/variant label")
                command.add_argument("--track", choices=("SYNTHETIC_PUBLIC", "PUBLIC", "PRIVATE_LOCAL"),
                                     required=True)
                command.add_argument("--run-id", required=True)
                command.add_argument("--ks", default="1,5,10,20", help="frontier K values for all lanes")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.verb == "retrieve":
            result = _retrieve_command(args)
            if args.action == "lane-rescue":
                result = {key: result[key] for key in ("population", "lane_rescue",
                                                       "lane_overlap_candidates", "lane_overlap_truths")}
            elif args.action == "ablate":
                result = {"population": result["population"], "candidate_availability":
                          result["leave_one_lane_out_candidate_availability"]}
        else:
            records = _inputs(args)
            if args.action == "profile":
                result = profile(records)
            elif args.action == "schema":
                result = {"schema_version": ENTITY_VERSION, "valid": True, "rows": len(records),
                          "fields": [{"name": f.name, "type": str(f.type), "nullable": f.nullable}
                                     for f in ENTITY_SCHEMA]}
            else:
                digest = dataset_fingerprint(records)
                result = {"dataset_fingerprint": digest}
                if args.split_json:
                    split = read_json(args.split_json)
                    members = tuple(tuple(k) for k in split["members"])
                    if not set(members) <= {(r.source, r.entity_id) for r in records}:
                        raise ValueError("split references entities outside the dataset")
                    result["split_fingerprint"] = split_fingerprint(
                        digest, split["name"], split["purpose"], members, split.get("cohort_metadata"))
        sys.stdout.buffer.write(canonical_json(result) + b"\n")
        return 0
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(f"concord: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
