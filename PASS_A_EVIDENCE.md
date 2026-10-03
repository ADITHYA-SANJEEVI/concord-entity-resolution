# Pass A: current synthetic evidence

Producing implementation: `0ead99612ce93d47e51d748d3ecc01a026a92864` (clean on both platforms).
Identity epoch: `concord.neutral-reference.v1`. These runs establish new source,
configuration, schema, model metadata and artifact lineage identities. Prior
bundles are superseded; changed bytes do not retain prior cryptographic identities.

All inputs are invented and publicly distributable. Results describe the declared
fixtures and workloads. They do not establish independent real-world quality.

## Retrieval results

| Synthetic population | Queries | Targets | Candidates | Truths recovered | Truth recall |
|---|---:|---:|---:|---:|---:|
| Small fixture | 9 | 12 | 12 | 8 / 9 | 0.888889 |
| Reference DF fixture | 200 | 200 | 272 | 200 / 200 | 1.000000 |

Small-fixture reduction ratio is 0.750000;
zero-candidate queries are 2 / 9.
The script executes repeat, frontier, lane-rescue and ablation surfaces.
Candidate fingerprints repeat within each platform, and both platform summaries
agree exactly. Each platform verified 6 manifests and 41 artifacts.


The [compact bundle](docs/evidence/PASS_A_RUNS.json) retains manifests,
physical hashes, producing source inventory, logical identities, environment and
resource observations. Full model/stage tables remain under
`outputs/neutral-current-pass-a-windows` and
`outputs/neutral-current-pass-a-linux`.

See [reproduction](docs/REPRODUCIBILITY.md) and
[usage](docs/PASS_A_USAGE.md) for commands and contract semantics.
