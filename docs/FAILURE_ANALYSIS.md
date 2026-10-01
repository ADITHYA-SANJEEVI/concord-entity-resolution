# Failure analysis

## Submitted-system failure modes

- Retrieval misses: a true link absent from all five top-K views cannot be recovered by the classifier.
- Cross-script variation: transliteration features improved the selected development score, but heavily transliterated or non-Latin records remain difficult.
- Sparse addresses: missing or weak address evidence reduces separation among similar business names.
- Ambiguous short names: common or franchise-like names can produce several plausible owners.
- Target competition: a locally plausible pair can lose global ownership to another Source-1 record.
- Cardinality errors: a fixed pair threshold does not explicitly optimize the number of targets assigned to each Source-1 record.
- Distribution shift: France appeared only at test time in the preserved evidence, so labeled calibration was limited to US and India.

## Lessons from rejected work

- More candidates can improve retrieval oracle while reducing end-to-end F0.5 if scoring and operational cost do not remain controlled.
- Ranking improvements do not guarantee a better deployable threshold policy. The XGBoost ranker improved oracle ordering but its native policy underperformed V1 on POLICY_DEV.
- Semantic models can show pairwise signal and still fail the final decision metric. Qwen and the later cross-encoder lanes illustrate this distinction.
- Hard-negative retraining can reduce a narrow inversion count while worsening overall F0.5.
- Learned cardinality, expected-F0.5 decoding, and zero-match abstention did not beat the fixed ownership-plus-threshold policy in their frozen qualifications.
- External web evidence added no accepted POLICY_DEV gain and was not part of the submitted system.

## Known reproducibility limits

The current machine has not performed a complete raw-data regeneration of the 87,934,151-pair test graph. The preserved output hashes, validator evidence, source compilation, and reduced contract execution are strong evidence for the frozen artifact, but they are not a substitute for a future high-memory Linux clean-room run.
