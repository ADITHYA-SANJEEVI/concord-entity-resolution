"""Regression: platform audit distinguishes policy identity from numeric diagnostics."""

import runpy
from dataclasses import replace
from pathlib import Path

from concord.c3_contracts import FailureAttribution


def logical_failures():
    return runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/retain_pass_c_evidence.py"))["logical_failures"]


def example():
    return FailureAttribution("q", "t", "FALSE_NEGATIVE", "SCORING", (),
        (("retrieved", True), ("score", .63), ("is_owner", False),
         ("rival_s1_id", "r"), ("rival_margin", -.1)))


def test_failure_identity_ignores_model_numbers_only():
    row = example()
    changed = replace(row, diagnostics=tuple((k, v + 1e-9 if k in ("score", "rival_margin") else v) for k, v in row.diagnostics))
    assert row != changed
    assert logical_failures()((row,)) == logical_failures()((changed,))


def test_failure_identity_preserves_policy_evidence():
    row = example()
    changes = [replace(row, failure_stage="OWNERSHIP"), replace(row, tags=("ZERO_MATCH",))]
    for key, value in (("retrieved", False), ("is_owner", True), ("rival_s1_id", "another")):
        changes.append(replace(row, diagnostics=tuple((k, value if k == key else v) for k, v in row.diagnostics)))
    assert all(logical_failures()((row,)) != logical_failures()((changed,)) for changed in changes)
