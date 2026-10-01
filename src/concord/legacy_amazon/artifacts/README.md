# Historical model artifacts

This directory keeps the exact ordered feature schema and LightGBM configuration from the verified Amazon package.

The trained `cross_script_59_reproduced_model.joblib` and its LightGBM text export are intentionally omitted. They were trained from organizer-provided data, and the available workspace does not establish public redistribution rights. Their hashes, sizes, model structure, and provenance are recorded in `archive_manifest/artifacts.json` and `docs/REPRODUCIBILITY.md`.

To run the historical pipeline in an authorized private environment, place the verified model files in this directory and confirm their SHA-256 values before execution.
