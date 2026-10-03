# Concord Pass A usage and semantics

This guide covers implemented C1 contracts and C2 retrieval. C3 resolution and
C4 research are documented in the other usage guides.

## Installation and public reproduction

Python 3.12 is the verified interpreter line. On Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/reproduce_pass_a.py --output outputs/pass-a-demo
```

On Linux use `python -m venv .venv` and `.venv/bin/python` instead. The CI matrix
executes the public suite on Windows and Ubuntu. Output directories must be new or
empty: previous results and failed manifests are retained.

The reproduction script executes an invented 9-query/12-target fixture through all
C2 CLI surfaces, repeats its candidate hash, and separately runs a 200-query/200-target
invented corpus with the strict reference configuration. These are P0 synthetic
measurements of the declared invented fixtures. Every quality report has a run manifest.

## Inspect

```text
concord inspect profile --entities entities.parquet
concord inspect schema --entities entities.parquet
concord inspect fingerprint --entities entities.parquet --split-json split.json
```

`split.json` contains `name`, `purpose`, `members` as `[source, entity_id]` pairs,
and optional `cohort_metadata`. CLI validation rejects members outside the dataset.
The low-level fingerprint primitive validates identities but cannot validate dataset
membership from a digest alone.

The existing external fixtures can be inspected directly:

```text
concord inspect profile --source1 examples/synthetic/source1.tsv --source2 examples/synthetic/source2.tsv --source3 examples/synthetic/source3.tsv
```

TSV is an external fixture adapter. Present empty cells remain empty. An absent
country column means `None`; there is no TSV string sentinel for null text.
Use typed Parquet to distinguish null text from empty strings.

## Retrieve

```text
concord retrieve run --entities entities.parquet --truth truth.json --output outputs/run-1 --population P0/my-fixture-v1/dev --track SYNTHETIC_PUBLIC --run-id run-1
concord retrieve frontier --entities entities.parquet --truth truth.json --output outputs/frontier-1 --population P0/my-fixture-v1/dev --track SYNTHETIC_PUBLIC --run-id frontier-1 --ks 1,5,10,20
```

`lane-rescue` and `ablate` take the same inputs and retain the full report while
printing their diagnostic surface. Truth is optional for `run`, `lane-rescue`,
and `ablate`; undefined quality statistics are null. An empty labelled truth set
also has undefined recall, not a fabricated perfect score. `frontier` requires labels.

`truth.json` is a JSON list of `[s1_id, target_id]` pairs. Duplicate labels, unknown
IDs, and truths outside the eligible country universe are rejected. A label error
after graph generation produces a retained `FAILED` manifest and graph freeze.

The default is `reference-five-view-v1`: budgets `(5,5,5,10,8)`, reference
`min_df=2`, `max_df=0.05`, seed 0, fit cap 3,000,000. This is the reference
parameter/reference baseline, with the explicitly versioned new Concord order and
failure adapters described below. Name is `char_wb` trigrams,
compact is character trigrams, address uses `[a-z0-9]+` word tokens. Combined stacks
name and address vectors multiplied by float32 `sqrt(0.5)` without re-normalization.
Reverse retrieves S1 neighbors from each target using the combined vectors.

Tiny fixtures may yield empty reference vocabularies. Warnings are recorded, and
those lanes are empty. There is no automatic cutoff relaxation or Cartesian fallback.
This is the new Concord `concord.warn-empty-lane.v1` compatibility/fail-safe adapter,
fingerprinted as `empty_vocabulary_policy`. Reference `fit_transform()` raises on
the same fitting error; the warning/empty lane is not exact reference failure behavior.
Use `--profile synthetic` explicitly for `synthetic-five-view-v1` (`min_df=1`,
`max_df=1.0`). This is a fixture configuration, never a silently promoted reference
baseline. `--config config.json` can select validated immutable parameters. Reference
K/lane variants use `reference-budget-variant-v1`; they keep frozen vectorizer settings.
No transliteration, adaptive-K, or other retrieval challenger is implemented.

## Contract adapters and bounds

- Non-null normalization is the exact reference NFKD / combining-mark removal /
  casefold sequence. `None` stays `None`. The version includes the Unicode database
  identity, so a different interpreter's Unicode database is not silently equivalent.
- Compact names remove ASCII spaces only, matching reference retrieval; tabs and
  newlines are not stripped. Compact is a retrieval view, not base normalization.
- Missing text maps to an empty vectorizer input only in retrieval, with explicit
  missingness flags. Raw and normalized Parquet tables preserve it.
- Country labels are opaque. Retrieval partitions by exact equality; null-country
  queries compare with null-country targets. Null is distinct from the empty label.
- Input ordering is canonical before fitting/sampling and retrieval. Sparse top-N
  cutoff ties use the pinned library on canonical input order. Selected hits are
  ranked by similarity descending then neighbor ID ascending. No claim is made that
  top-N cutoff ties select the globally lexicographically smallest neighbor.
- Reference ranks are zero-based; the new API adds one. Missing lane evidence is
  absent (Parquet null), never a magic sentinel. Mask bits remain `1,2,4,8,16`.
- Entity identity is `(source, entity_id)`. Because the frozen candidate key is
  `(s1_id, target_id)`, target IDs shared between S2 and S3 are rejected explicitly;
  datasets with such collisions need a reversible external ID adapter.
- With `Q` queries and `T` targets in each country, the global edge bound is
  `Q * (K_name + K_compact + K_address + K_combined) + T * K_reverse`, capped by
  the eligible Cartesian size. Reverse does not impose a per-S1 degree cap.
- All similarity products use chunked sparse top-N. Records and the bounded union
  are held in memory; this Pass A implementation does not claim reference-scale
  memory parity or disk-backed execution.

## Reference parameter/function parity and sampling boundary

`sampling_order_policy = "concord.source-id.queries-then-targets.v1"` is immutable
and included in configuration fingerprints and manifests. Each country population
is sorted by `(source, entity_id)`, with all S1 queries followed by S2/S3 targets.
Fit evidence records that policy, population/sample counts, whether the cap applied,
the selected identity fingerprint, and `reference_capped_sample_parity = "UNVERIFIED"`.

Reference non-null `fold()` parity, vectorizer parameter parity, and five-lane sparse
function/reference parity on uncapped fixtures are supported. Seeded sampling of
canonical order is deterministic. The reference sampler instead selects seeded
positions in reference q/t materialization order. Above FIT_CAP=3,000,000, identical
RNG positions need not identify identical records when those orders differ.

**UNVERIFIED PRIVATE CAPPED-SAMPLE / FULL-GRAPH PARITY:** reference capped-sample
membership has not been reproduced. Exact reference-scale candidate-graph parity
is not claimed. No private row order is reconstructed and canonical ordering is
retained. Tests exercise the real cap boundary with numeric positions and compare
sample membership against the reference sampler on an explicitly reduced-cap public
fixture. That comparison demonstrates the order distinction, not private parity.

## Metric and evidence interpretation

Truth-pair recall uses labelled eligible pairs as its denominator. Candidate
density and zero-candidate rate include all S1 records, including zero-truth queries.
Reduction Ratio uses the sum of country-eligible query × target universes.

Recall@1/5/10/20 is per forward lane, plus an explicitly named union of forward
lane top-K sets. It is not a global scorer ranking. Reverse ranks target-to-query
neighbors, so query Recall@K for reverse is undefined. Existing configured K bounds
still apply; requesting Recall@20 does not generate additional hits.

Lane rescue means truths unique to that lane after union; overlap counts candidates
and truths separately. Marginal recall per million added comparisons is undefined
when the lane contributes no unique candidates. Leave-one-lane-out reports remove
only that lane's evidence. A multi-lane candidate remains available; no final decision
survival or structural stability conclusion follows.

Frontier reports retain every config, candidate artifact, fit-sample identity,
warning, and Pareto flag. SVG plots show recall versus pair count, runtime, and
process peak RSS. No configuration is promoted. Runtime and CPU time measure the
retrieval call, not the entire CLI. OS-reported process-lifetime peak RSS (Windows
`peak_wset`, Linux `getrusage.ru_maxrss`) and sampled psutil RSS are both recorded.
The separate OS counters can disagree transiently; both values remain unaltered.
They include interpreter/dependencies; frontier points share a
process, so their memory high-water can include earlier configurations. Artifact
byte totals exclude the manifest itself; input bytes count the explicitly read files.

Manifests are instances of `concord.experiment.v1`, validated against the separate
packaged Draft 2020-12 schema. Metrics carry population, units, evidence class, and
producing run. Artifact lineage records contain physical hashes and producing config
identity; logical dataset, split, truth, and candidate identities are also retained.
Different runs/configurations may produce identical bytes and share a content DAG
node while preserving separate producing observations. Timestamps, environment, and
local paths never enter logical dataset/split fingerprints.

Execution failures are marked `FAILED` and validated before final manifest writes.
The original execution exception remains primary. If failure-manifest validation
also fails, both errors are reported, `failed_manifest_errors.json` marks the evidence
`INVALID`, and a serializable snapshot is saved as `manifest.failed.unvalidated.json`.
It does not overwrite the last validated manifest. Diagnostic-write errors are
reported separately without hiding the execution failure. Such snapshots are not
valid completed-run evidence.
