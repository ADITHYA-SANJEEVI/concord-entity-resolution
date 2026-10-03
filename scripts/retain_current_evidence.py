"""Verify clean C1-C4 runs and retain compact current Concord evidence."""

import argparse
import platform
from pathlib import Path

from retain_pass_c_evidence import compact

from concord.c3_cli import verified_run
from concord.cli import _environment
from concord.metadata import ArtifactLineage, read_json, validate_lineage, write_json
from concord.provenance import sha256_file


def retain(directory, label, output):
    root = Path(__file__).resolve().parents[1]
    directory = Path(directory).resolve()
    sources = _environment()["implementation_source_sha256"]
    manifests, identities, commits = {}, [], set()
    for path in sorted(directory.rglob("manifest.json")):
        manifest = verified_run(path.parent)
        if manifest["git"]["dirty"]:
            raise ValueError("retained evidence requires clean producing code")
        if manifest["operational"]["environment"]["implementation_source_sha256"] != sources:
            raise ValueError("producing source differs from the current implementation")
        commits.add(manifest["git"]["commit_sha"])
        manifests[path.parent.relative_to(directory).as_posix()] = manifest
        for item in manifest["artifacts"].values():
            fields = dict(item["lineage"])
            fields["parent_sha256"] = tuple(fields["parent_sha256"])
            identities.append(ArtifactLineage(**fields))
    if not manifests or len(commits) != 1:
        raise ValueError("evidence requires manifests from one producing commit")
    validate_lineage(tuple(identities))
    summaries = {p.relative_to(directory).as_posix(): compact(read_json(p))
                 for p in sorted(directory.glob("**/summary.json"))}
    files = {p.relative_to(directory).as_posix(): {"sha256": sha256_file(p),
             "bytes": p.stat().st_size} for p in sorted(directory.rglob("*"))
             if p.is_file() and (p.name in ("summary.json", "manifest.json", "reproduction.json")
                                 or "logs" in p.relative_to(directory).parts)}
    bundle = {"schema_version": f"concord.pass-{label.lower()}-evidence.v2",
              "evidence_class": "D", "identity_epoch": "concord.neutral-reference.v1",
              "platform": platform.system().lower(),
              "artifact_root": directory.relative_to(root).as_posix(),
              "producing_commit": next(iter(commits)), "manifests": manifests,
              "verified_artifact_count": len(identities), "summaries": summaries,
              "retained_file_identities": files,
              "claim_boundary": "Invented publicly distributable fixtures; measured workloads only."}
    write_json(output, bundle)
    return bundle


def main():
    parser = argparse.ArgumentParser()
    for label in ("a", "b", "c"):
        parser.add_argument(f"--pass-{label}", required=True)
    args = parser.parse_args()
    for label in ("a", "b", "c"):
        result = retain(getattr(args, f"pass_{label}"), label,
                        f"docs/evidence/PASS_{label.upper()}_RUNS.json")
        print(label.upper(), result["verified_artifact_count"], result["producing_commit"])


if __name__ == "__main__":
    main()
