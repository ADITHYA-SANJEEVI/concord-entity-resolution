# Results

## Selected baseline

| Measure | Value | Evidence level |
|---|---:|---|
| Public leaderboard Macro F0.5 | 0.955136 | Portal evidence and confirmed submission chronology |
| POLICY_DEV Macro F0.5 | 0.9593640004712406 | Qualification and exact reproduction gate |
| POLICY_DEV TP / FP / FN | 9,826 / 162 / 757 | Qualification report |
| Test Source-1 rows | 1,732,544 | Frozen outputs and official validator |
| Valid target IDs | 9,969,589 | Official validator with ID checking |
| Candidate pairs | 87,934,151 | Graph and score manifests |
| Accepted links | 5,708,382 | Ownership completion manifest |
| Empty matching rows | 100,939 | Official validator |

The development and public values refer to different evaluation populations and should not be compared as if they were repeated measurements of one split.

## Output verification

The frozen candidate and matching TSVs each contain 1,732,544 data rows. A memory-bounded paired scan verified exact headers, strict and aligned Source-1 ordering, unique target IDs within rows, valid S2/S3 prefixes, and that every emitted match occurs in the corresponding candidate row. There were zero empty candidate rows.

## Full regeneration status

Source, schema, configuration, output hashes, and reduced contract tests are preserved. A full clean-room regeneration of all 87,934,151 pairs has not been run in the current native Windows environment. That limitation does not change the identity of the frozen, validated outputs.
