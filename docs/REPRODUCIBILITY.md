# Reproducibility

## Preserved

- Exact historical Python source for retrieval, 55-feature generation, cross-script features, scoring, finalization, comparison, and validation.
- Exact 59-feature order and feature definitions.
- Exact LightGBM configuration.
- Required Python package versions from the verified package.
- Model hashes, model type, 600-tree count, 59-feature count, and training-row count.
- Output hashes, row counts, link counts, and validator evidence.
- Resource requirements and deterministic ordering rules.

## Intentionally omitted

Organizer datasets, feature matrices, candidate graphs, output TSVs, caches, SQLite databases, Parquet files, ZIP archives, and model weights are not committed.

The trained model is omitted even though its files are only 1.9 MB and 4.2 MB. It was trained from organizer-provided data, and the workspace contains no clear grant allowing public redistribution. The omission is a rights decision, not a size decision.

Verified model identities:

```text
cross_script_59_reproduced_model.joblib
c5b0e2246794f5e79d6cfed1e16d82040d682bdee4cf94eccb760d61e69d6610

cross_script_59_reproduced_model.txt
7c1797a78d4585647c818868a1d8960790cd2a5f77b9c90a36af9a2a4c710784
```

The historical model was a deterministic refit because the original serialized model had not been retained. POLICY_DEV raw probabilities differed by at most `1.9653723093426834e-11`, while selected ownership, emitted links, TP, FP, FN, and Macro F0.5 matched exactly.

## Private replay procedure

1. Obtain the organizer data and verified model artifacts through an authorized channel.
2. Confirm all hashes in `archive_manifest/artifacts.json`.
3. Use Linux or WSL2 with Python 3.12, 32 workers, about 128 GB RAM, and at least 35 GB temporary disk.
4. Install `.[amazon]`.
5. Place the two verified model files under `src/concord/legacy_amazon/artifacts/`.
6. Run the historical pipeline with separate train, test, work, and output directories.
7. Compare regenerated outputs with the frozen hashes.
8. Run the historical validator with ID checking.

The source expects organizer data and the model to exist. Missing private artifacts should fail explicitly rather than cause a substitute model or dataset to be used.
