# Pipeline

## Inputs

Expected organizer files are `train_source1.tsv`, `train_source2.tsv`, `train_source3.tsv`, `train_ground_truth.tsv`, `test_source1.tsv`, `test_source2.tsv`, and `test_source3.tsv`. They are private inputs and are not part of this repository.

## Stages

1. `retrieve`: normalize records, fit sparse vectorizers, run five top-K views, union pairs, and export the candidate graph.
2. `features`: calculate the ordered 55 base features over the complete graph.
3. `score`: append four cross-script features, validate the 59-column schema, and run LightGBM probabilities.
4. `finalize`: resolve global target ownership, apply inclusive 0.64 thresholds, and write deterministic TSVs.
5. `validate`: check headers, Source-1 coverage, ID membership, duplicates, prefixes, row alignment, and the rule that matches are a subset of candidates.

The entry point is `python -m concord.legacy_amazon.run_pipeline`. Individual stages support restart through the same work directory.

## Determinism

- Retrieval sampling uses NumPy generator seed 0.
- Model training used random seed 42.
- Candidate keys, graph partitions, ownership ties, and emitted ID lists have explicit ordering.
- The model and schema are hash-checked before scoring.
- Output equality is checked with SHA-256 and streaming comparison utilities.

## Production resources

Historical production used 32 workers and high-memory Linux infrastructure. The available evidence recommends at least 128 GB RAM and 35 GB of free temporary disk. A comparable full run was estimated at roughly 2.5 hours. Native Windows is not supported by the feature implementation because it requires multiprocessing `fork`.
