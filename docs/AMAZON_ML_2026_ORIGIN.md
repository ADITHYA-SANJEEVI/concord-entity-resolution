# Amazon ML Challenge 2026 origin

## Origin

Concord evolved from earlier Amazon ML Challenge 2026 business entity-resolution work. The current Concord project is individually architected, implemented, tested and documented by Adithya Sanjeevi. The preserved challenge submission has separate historical provenance; this document does not assign sole authorship of that submission.

The task provided a deduplicated Source 1 and two target collections, Source 2 and Source 3. For every Source-1 business, a system had to return zero, one, or many matching target identifiers. A target could not be assigned to multiple Source-1 owners in the final system. Performance was measured with macro F0.5, which weights precision more heavily than recall.

## Scale

The verified test population contained 1,732,544 Source-1 rows and 9,969,589 valid Source-2 and Source-3 target identifiers. The submitted candidate graph contained 87,934,151 unique pairs. The final output accepted 5,708,382 links and left 100,939 Source-1 rows empty.

## Submitted architecture

The system responsible for the preserved public result used:

1. Country-partitioned normalization.
2. Five sparse TF-IDF retrieval views.
3. A unioned and deduplicated candidate graph.
4. Fifty-five direct, string, numeric, retrieval-rank, and graph-context features.
5. Four transliteration and cross-script features.
6. A 59-feature `LGBMClassifier`.
7. Global target ownership by score descending and `s1_id` ascending.
8. A fixed 0.64 threshold for both S2 and S3.
9. Deterministic output ordering and structural validation.

The public leaderboard result associated with the preserved submission was Macro F0.5 0.955136. The selected POLICY_DEV result was 0.9593640004712406.

## Frozen submission identity

| Artifact | SHA-256 |
|---|---|
| `Aurorawave_submission.zip` | `d0574aab454f2e4798986ed5b488411bd04937b27ac6a9c17601235d4f07618e` |
| `matching_results.tsv` | `0153c2ad53f0cfbecce5339075968588d131d3144f6c85c49bb2a5a05741d145` |
| `candidate_pairs.tsv` | `709164321b318e89763b37277dbcb2e96e40ccdcec93091bfe96c01a6e30a526` |

These files are not committed. Their identities and local paths are recorded in `archive_manifest/final_submission.json` and `archive_manifest/artifacts.json`.

## Later work

The selected test production was completed on September 27, 2026, before the later external-evidence, external candidate-rescue, web-identity, and final meta-decoder experiments. Those branches did not contribute to the packaged 0.955136 submission. Earlier and later XGBoost, Qwen, model2vec, cross-encoder, cardinality, expected-F0.5, oracle, and decision-policy experiments are also excluded from the submitted architecture unless the experiment ledger explicitly says otherwise.

The repository does not claim Top 50, Top 100, PPI selection, or other unsupported recognition.
