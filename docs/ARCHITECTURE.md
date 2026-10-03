# Concord architecture

C1 owns typed entity, normalization, split, experiment and artifact contracts.
C2 builds a bounded sparse graph without labels. C3 computes features, fits a
scorer, arbitrates ownership, emits match sets, and evaluates them. C4 executes
diagnostic experiments against those same policy boundaries.

Entities preserve raw text, source and country. NFKD/casefold normalization
distinguishes null from empty. Retrieval adapters materialize name, compact name,
address and equal-weight combined TF-IDF representations; reverse search uses
the combined view. Canonical source/ID ordering precedes seeded fit sampling.
Empty vocabularies produce recorded empty lanes. Country is an eligibility key.

The default `reference-five-view-v1` profile fixes budgets (5,5,5,10,8), min_df=2,
max_df=0.05 and a 3,000,000-record vectorizer fit cap. `synthetic-five-view-v1`
uses min_df=1/max_df=1 for small invented fixtures. Reverse K is per target.

Features use the declared vectorizer fit population and coordinate-only cosine
products. All 59 columns have immutable names, definitions and order. Graph context
includes query/source rank, target rank, best-score deltas, rival margins and counts.
The four cross-script features use raw text with Unidecode and Unicode script names.

LightGBM requests 600 trees, learning_rate=0.05, num_leaves=63,
min_child_samples=100, reg_lambda=1, full row/column sampling, seed 42, deterministic
column-wise fitting and one thread. Actual tree count and trained model bytes are
recorded. Ownership selects score DESC/query ID ASC; threshold 0.640 applies only
to owners. Every query receives a sorted unique target set, including the empty set.

Bulk evidence is versioned Parquet. JSON manifests describe physical artifacts,
logical identities and parent DAGs. Scoring, ownership, disposition, resolution,
evaluation and failure attribution remain separate artifacts. Verification checks
bytes and declared lineage before downstream consumption.

`reference_baseline` contains independent numerical functions exercised by parity
tests, not a second CLI pipeline. They preserve vectorizer, sampler, rank, SQL-window
and cross-script semantics. Tests explicitly exercise materialization-order and
empty-vocabulary differences from current Concord behavior.

See [C1–C2](PASS_A_USAGE.md), [C3](PASS_B_USAGE.md), and [C4](PASS_C_USAGE.md)
for precise API and evaluation semantics.
