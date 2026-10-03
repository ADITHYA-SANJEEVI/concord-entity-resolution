# Concord

**Large-Scale Entity Resolution System**

Concord resolves entities with bounded retrieval, learned scoring, global target
ownership, deterministic decoding, and reproducible failure attribution.

## Why Concord exists

Names and addresses vary across sources, scripts, spelling, and missing fields.
Comparing every record with every possible target quickly becomes impractical.
Even a strong pair classifier can assign the same target to conflicting queries
or miss a match that retrieval never considered. Concord treats candidate coverage,
pair scores, ownership, and final match sets as separate, inspectable decisions.

## System architecture

```text
Typed entities → normalization → bounded multi-view retrieval
              → ordered features → learned pair scores
              → global target ownership → deterministic match sets
              → evaluation, failure attribution, and artifact evidence
```

| Layer | Implemented behavior |
|---|---|
| C1: contracts | Immutable records, null/empty semantics, canonical identities, versioned Parquet and JSON |
| C2: retrieval | Country partitions; name, compact name, address, combined, and reverse sparse TF-IDF views |
| C3: resolution | 59 ordered float32 features, LightGBM training/scoring, ownership, decoding, set evaluation |
| C4: research | Logistic comparison, feature/retrieval ablations, input perturbations, failure atlas, measured scale |

Normalization uses Unicode NFKD, removes combining marks, and case-folds text.
Retrieval and cross-script features retain their own declared representations.
Raw input and candidate-lane evidence remain available throughout the pipeline.

## Core engineering

- **Bound the graph.** Forward budgets are 5/5/5/10 per eligible query; the reverse
  view adds at most 8 incoming query edges per target. Sparse products avoid a dense
  all-pairs matrix. Features are computed only for retrieved pairs.
- **Keep feature order explicit.** The schema identifies all 59 column definitions:
  text/numeric similarity, exact cosines, retrieval ranks, graph context, and four
  cross-script signals. Training and loading verify schema identity.
- **Separate learning from policy.** The scorer emits probabilities. Ownership
  chooses each target's winner by score descending, then query ID ascending.
  The reference decoder accepts owners with score at least 0.640. Rejected edges
  retain dispositions; every evaluated query gets an empty, single, or multi-target set.
- **Prevent leakage.** Committed plans separate training, calibration, and test
  entities. Negative mining and model fitting use training labels only. Ablations
  retrain while preserving column order and the reference decoding policy.
- **Make decisions repeatable.** Canonical ordering, explicit seeds, artifact hashes,
  parent lineage, and physical verification connect outputs to their producing code.

## Evaluation

The committed evaluation uses **invented, publicly distributable synthetic fixtures**.
The C4 plan contains 320 training, 64 calibration, and 133 test queries with disjoint
entity identities. Shared generator templates limit what these results establish.

The suite measures macro set precision/recall/F0.5, exact-set accuracy, retrieved-pair
calibration, paired bootstrap differences, failure-stage movements, and decision
changes under perturbations. The scale recipe runs 128, 512, and 2,048 source queries,
with one warmup and three measured repetitions per size. Timings and sampled process
RSS describe those workloads; they do not establish production capacity.

Current measurements and producing identities are in [Pass A](PASS_A_EVIDENCE.md),
[Pass B](PASS_B_EVIDENCE.md), and [Pass C](PASS_C_EVIDENCE.md). Model comparisons are
diagnostic; the suite does not automatically promote a scorer or tune the threshold.

## Failure attribution

False negatives follow the earliest applicable policy gate: **RETRIEVAL** when the
truth pair is absent, **SCORING** below threshold, **OWNERSHIP** when another query
wins, and **DECODING** when an admissible owner is missing from the output. False
positives use score/policy evidence. **AMBIGUOUS** requires an explicit label or data
conflict annotation. Missing artifacts raise errors. This is deterministic stage
attribution; it does not prove a causal explanation for a model error.

## Reproducibility

Logical dataset, split, candidate, score, and resolution fingerprints complement
physical file hashes. Manifests retain configuration, schema, model, parent artifact,
package, source-byte, and Git identities. Output directories retain models, typed
stage tables, reports, and logs locally. Evidence bundles commit compact metadata.

The neutral reference and schema identities are newly established Concord artifacts.
Evidence is regenerated from a clean producing commit; changed bytes receive new
hashes. Model bytes and floating-point probabilities need not match across platforms.
See [reproduction and evidence](docs/REPRODUCIBILITY.md).

## Running Concord

Python 3.12:

```bash
python -m venv .venv
# Activate .venv using your shell, then:
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check src tests scripts examples
python -m compileall -q src tests scripts examples
git diff --check

python scripts/reproduce_pass_a.py --output outputs/pass-a-demo
python scripts/reproduce_pass_b.py --output outputs/pass-b-demo
python scripts/reproduce_pass_c.py --output outputs/pass-c-demo
```

Each reproduction requires a new or empty output directory. Run `concord --help`
for the CLI. Detailed contracts and commands: [C1–C2](docs/PASS_A_USAGE.md),
[C3](docs/PASS_B_USAGE.md), [C4](docs/PASS_C_USAGE.md).

## Repository structure

```text
src/concord/
  contracts.py, normalization.py, identity.py, metadata.py, storage.py
  retrieval/           bounded candidate generation and coverage diagnostics
  features/            ordered feature definitions and graph computation
  modeling/            training, scoring, and verified model loading
  inference/           ownership, dispositions, decoding, and evidence
  evaluation/          set quality, calibration, and failure attribution
  research/            experiments, robustness, failure atlas, and scale
  reference_baseline/  numerical reference functions and artifact contracts
  schemas/             experiment manifest schema
examples/synthetic/    invented records, generators, and split plans
scripts/               public reproduction and evidence retention
tests/                 contracts, parity, pipeline, and research verification
docs/                  current usage, reproduction, and compact run evidence
```

## Limitations

Country blocking excludes cross-country pairs. Target IDs must be globally unique
across target sources. Exclusive target ownership cannot represent genuinely shared
targets. Retrieval caps can miss truth pairs; reverse edges do not impose a strict
outgoing cap per query. Graph-context feature computation and evidence generation
become costly as workloads grow. Synthetic fixtures do not establish real-world
multilingual quality, general calibration, or throughput on larger corpora.

## Authorship

Individual project by **Adithya Sanjeevi**.
