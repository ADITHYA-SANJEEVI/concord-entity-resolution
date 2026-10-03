# Reproduction and current evidence

Install Python 3.12 and `python -m pip install -e ".[dev]"`. From a clean checkout:

```bash
python -m pytest -q
python -m ruff check src tests scripts examples
python -m compileall -q src tests scripts examples
git diff --check
python scripts/reproduce_pass_a.py --output outputs/current-pass-a
python scripts/reproduce_pass_b.py --output outputs/current-pass-b
python scripts/reproduce_pass_c.py --output outputs/current-pass-c
```

Pass A exercises normalization/retrieval, repeat candidate identity, coverage,
frontiers, lane rescue and ablations, plus a stricter DF fixture. Pass B trains and
repeats the reference model, verifies resolution identities, evaluates calibration
and test populations, attributes errors, and exports query evidence. Pass C fits
reference and diagnostic models, runs six feature ablations and retrieval variants,
perturbs inputs, checks ordering/repeats, and measures the full scale recipe.

Generated models, Parquet, logs and environments remain in ignored directories.
Keep those directories to independently verify compact evidence. Retention scripts
verify all manifest files and parent identities, clean producing Git state, and
current implementation bytes before writing `docs/evidence/PASS_*_RUNS.json`.

Single-platform retention:

```bash
python scripts/retain_current_evidence.py --pass-a outputs/current-pass-a --pass-b outputs/current-pass-b --pass-c outputs/current-pass-c
```

The optional two-platform C4 check uses independently reproduced Windows and Linux
runs and requires matching resolution sets, set quality, logical failure attribution
and robustness query sets. It records probability deltas separately:

```bash
python scripts/retain_pass_c_evidence.py --windows outputs/windows-pass-c --linux outputs/linux-pass-c --output docs/evidence/PASS_C_RUNS.json
```

Evidence has two commits: a clean implementation producer, followed by a compact
evidence commit. This avoids recording an evidence file as its own producer.
Environment metadata includes package versions, Python, OS, process resource
observations and source hashes. Reproduce within a platform for model-byte equality;
cross-platform floating-point or model-byte equality is not guaranteed.

## Neutral identity migration

The current reference module is a reduced set of numerical contract functions.
Archive-only runners, output validators, private-artifact manifests, prior metrics,
and superseded design/audit documents were removed. Required reference functions
and column definitions were retained; attribution-bearing identities were replaced
with Concord technical names. Documentation now describes implemented C1–C4.

Retrieval profile IDs, feature/decoder versions, feature definition versions, fit
evidence fields and seed-policy configuration changed. Their hashes, model metadata,
artifact parent DAGs and source manifests therefore change. The neutral reference
schema no longer embeds unavailable training/cache/source digests. New synthetic
runs establish new identities; prior bundles are superseded, not edited to claim
hash continuity. Numerical thresholds, feature order and budgets remain fixed.

## Documentation classification

Authoritative: README, architecture, reproduction, and the three usage guides.
Current evidence: the three root evidence reports and compact JSON bundles.
Useful reference: `reference_baseline` contract artifacts and parity tests.
Superseded proposals, origin records, archive manifests and archaeological audits
were removed from the working tree. Git history was left intact.
