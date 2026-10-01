# Provenance

## Authority order

When historical records disagree, use this order:

1. Frozen file bytes and independently recomputed SHA-256 values.
2. Validator, score, ownership, and graph manifests tied to those hashes.
3. Exact source and configuration from `amazon_ml_final_package`.
4. Audit documents and experiment reports.
5. Timestamp-based chronology and contextual notes.

## Selected lineage

The selected candidate graph came from the full five-view sparse retrieval run. The selected model family added four cross-script features to the frozen 55-feature matrix. The serialized model in the package was a deterministic reproduction whose final POLICY_DEV decisions matched exactly. It then scored the complete frozen test graph once. The fixed global-ownership and 0.64 policy produced the selected matching output.

## Integrity controls

- Source and artifact hashes were verified locally during archival preparation.
- Complete score and graph manifests recorded 87,934,151 aligned, unique pairs with finite scores.
- The finalizer verified global ownership and the fixed decision policy.
- The official validator checked complete Source-1 coverage and target-ID membership.
- A paired streaming scan confirmed output alignment and match-subset integrity.
- No test labels or final holdout were present in the selected scoring path.
- No external lookup or pretrained semantic model contributed to the selected submission.

## Errata

One frozen qualification report recorded a malformed joblib hash with an extra character. The scoring path independently validated the actual 64-character joblib digest: `c5b0e2246794f5e79d6cfed1e16d82040d682bdee4cf94eccb760d61e69d6610`. The frozen report should not be silently rewritten.

An earlier audit mentions a different portal ZIP identity from an intermediate packaging stage. The final preserved file named `Aurorawave_submission.zip` was rehashed locally during this archival pass and is identified by `d0574aab454f2e4798986ed5b488411bd04937b27ac6a9c17601235d4f07618e`.

## Redistribution boundary

Organizer data and challenge-trained model files are not redistributed. Source code is preserved, but no license is asserted until ownership and challenge terms are reviewed. Later external-lookup experiments are documented for history and are not part of the selected competition methodology.
