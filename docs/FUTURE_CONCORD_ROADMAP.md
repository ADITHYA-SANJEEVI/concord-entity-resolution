# Future Concord roadmap

Everything in this document is future work unless a later commit explicitly marks it implemented and adds tests and evidence.

## Decision provenance

- Store auditable evidence for every accepted or rejected pair.
- Version entity decisions and make model, rule, and reviewer inputs traceable.
- Support reversible merges and splits rather than irreversible cluster mutation.

## Incremental computation

- Replace challenge-specific batch assumptions with Parquet and DuckDB ingestion.
- Recompute only affected neighborhoods when records or decisions change.
- Preserve stable identifiers and compare decision deltas across versions.

## Review workflow

- Route low-margin ownership conflicts and high-impact changes to human review.
- Record reviewer decisions, evidence, and reason codes.
- Evaluate review queues by downstream damage avoided, not only pair uncertainty.

## Evaluation

- Add public synthetic and licensed benchmark datasets.
- Test multilingual retrieval and transliteration without relying on private challenge data.
- Track pair quality, cluster consistency, calibration, runtime, memory, and incremental-update cost.

## Engineering

- Define stable interfaces across retrieval, features, modeling, inference, and evaluation.
- Add reproducible training recipes that use redistributable data.
- Run cross-platform tests where possible and isolate Linux-only high-scale paths.
