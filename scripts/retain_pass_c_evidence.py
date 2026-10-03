"""Verify two clean public runs and retain compact metadata, never model weights."""

import argparse
from pathlib import Path

import numpy as np

from concord.c3_cli import verified_run
from concord.c3_storage import read_stage
from concord.metadata import ArtifactLineage, read_json, validate_lineage, write_json
from concord.provenance import sha256_file


def compact(value):
    if isinstance(value, dict):
        return {k: compact(v) for k, v in value.items() if k not in ("per_query", "risk_coverage", "raw_confidence_diagnostics", "origin_by_pair")}
    if isinstance(value, list):
        return [compact(v) for v in value]
    return value


def logical_failures(rows):
    """Compare actual policy attribution, excluding model-dependent numeric diagnostics."""
    return [(r.s1_id, r.target_id, r.error_type, r.failure_stage, r.tags,
             r.attribution_policy_version,
             tuple((k, v) for k, v in r.diagnostics if k not in ("score", "rival_margin"))) for r in rows]


def retain(windows, linux, output):
    root = Path(__file__).resolve().parents[1]
    retained, originals = {}, {}
    source_package = root / "src/concord"
    for platform, directory in (("windows", Path(windows)), ("ubuntu_wsl", Path(linux))):
        manifests = {stage: verified_run(directory / stage) for stage in ("public", "scale")}
        identities = []
        for manifest in manifests.values():
            if manifest["git"]["dirty"]:
                raise ValueError("retained evidence requires clean producing code")
            for relative, digest in manifest["operational"]["environment"]["implementation_source_sha256"].items():
                if sha256_file(source_package / relative) != digest:
                    raise ValueError("producing source differs from the current implementation")
            for artifact in manifest["artifacts"].values():
                fields = dict(artifact["lineage"])
                fields["parent_sha256"] = tuple(fields["parent_sha256"])
                identities.append(ArtifactLineage(**fields))
        validate_lineage(tuple(identities))
        summary = read_json(directory / "public/summary.json")
        seed_a = read_stage(directory / "public/logistic/test/resolutions.parquet", "resolutions")
        seed_b = read_stage(directory / "public/logistic_seed7/test/resolutions.parquet", "resolutions")
        if [d.s1_id for d in seed_a] != [d.s1_id for d in seed_b]:
            raise ValueError("seed study query alignment mismatch")
        seed_changes = sum(a.accepted_targets != b.accepted_targets for a, b in zip(seed_a, seed_b, strict=True))
        originals[platform] = summary
        retained[platform] = {"artifact_root": directory.resolve().relative_to(root).as_posix(),
            "manifests": manifests, "manifest_file_sha256": {s: sha256_file(directory / s / "manifest.json") for s in manifests},
            "verified_artifact_count": sum(len(m["artifacts"]) for m in manifests.values()),
            "public_summary_sha256": sha256_file(directory / "public/summary.json"),
            "public_results": compact(summary), "scale_results": compact(read_json(directory / "scale/summary.json")),
            "logistic_seed_sensitivity": {"seeds": [42, 7], "query_count": len(seed_a),
                "changed_count": seed_changes, "decision_change_rate": seed_changes / len(seed_a)},
            "failure_atlas": read_json(directory / "public/failure_atlas_summary.json"),
            "logs": {p.relative_to(directory).as_posix(): {"sha256": sha256_file(p), "bytes": p.stat().st_size} for p in sorted((directory / "logs").glob("*"))}}
    w, linux_results = originals["windows"], originals["ubuntu_wsl"]
    for key in ("dataset_fingerprint", "split_plan_sha256", "recipe"):
        if w[key] != linux_results[key]:
            raise ValueError("platform dataset/split/recipe mismatch")
    comparison = {}
    for name in w["experiments"]:
        comparison[name] = {}
        if w["experiments"][name]["definition_sha256"] != linux_results["experiments"][name]["definition_sha256"]:
            raise ValueError("platform experiment definition mismatch")
        for role in ("calibration", "test"):
            a, b = (s["experiments"][name]["roles"][role] for s in (w, linux_results))
            wa = read_stage(Path(windows) / f"public/{name}/{role}/scores.parquet", "scores")
            la = read_stage(Path(linux) / f"public/{name}/{role}/scores.parquet", "scores")
            if [(s.s1_id, s.target_id) for s in wa] != [(s.s1_id, s.target_id) for s in la]:
                raise ValueError("platform scored graph mismatch")
            maximum = float(np.max(np.abs(np.array([s.score for s in wa]) - np.array([s.score for s in la])))) if wa else 0.
            exact_sets = a["resolution_fingerprint"] == b["resolution_fingerprint"]
            wf = read_stage(Path(windows) / f"public/{name}/{role}/failure_attribution.parquet", "failure_attribution")
            lf = read_stage(Path(linux) / f"public/{name}/{role}/failure_attribution.parquet", "failure_attribution")
            same_attribution = logical_failures(wf) == logical_failures(lf)
            if not exact_sets or a["quality"] != b["quality"] or not same_attribution:
                raise ValueError("platform logical result mismatch; retain a qualified report instead")
            comparison[name][role] = {"maximum_absolute_probability_delta": maximum,
                "probabilities_within_1e_minus_12": maximum <= 1e-12, "probability_equality_required": False,
                "score_fingerprints_equal": a["score_fingerprint"] == b["score_fingerprint"],
                "resolution_fingerprints_equal": exact_sets, "set_quality_equal": True,
                "logical_failure_attribution_equal": same_attribution,
                "failure_reports_including_numeric_diagnostics_equal": a["failures"] == b["failures"]}
    if {n: s["changed_queries"] for n, s in w["robustness"].items()} != {n: s["changed_queries"] for n, s in linux_results["robustness"].items()}:
        raise ValueError("platform robustness decisions differ")
    bundle = {"schema_version": "concord.pass-c-evidence.v1", "evidence_class": "D", "platforms": retained,
              "cross_platform_observations": comparison, "robustness_change_queries_equal": True,
              "claim_boundary": "Observed invented P0 fixture only; no general model-binary portability, reference/private parity, WDC quality, production throughput or automatic promotion."}
    write_json(output, bundle)
    return bundle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--windows", required=True)
    parser.add_argument("--linux", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    bundle = retain(args.windows, args.linux, args.output)
    print({k: v["verified_artifact_count"] for k, v in bundle["platforms"].items()})


if __name__ == "__main__":
    main()
