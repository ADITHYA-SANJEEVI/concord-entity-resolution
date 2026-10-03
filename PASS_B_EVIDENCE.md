# Pass B: current synthetic evidence

Producing implementation: `0ead99612ce93d47e51d748d3ecc01a026a92864` (clean on both platforms).
Identity epoch: `concord.neutral-reference.v1`. These runs establish new source,
configuration, schema, model metadata and artifact lineage identities. Prior
bundles are superseded; changed bytes do not retain prior cryptographic identities.

All inputs are invented and publicly distributable. Results describe the declared
fixtures and workloads. They do not establish independent real-world quality.

## Resolution results

| Held-out synthetic test metric | Value |
|---|---:|
| Queries | 16 |
| Macro precision | 0.625000 |
| Macro recall | 0.718750 |
| Macro F0.5 | 0.614583 |
| Exact-set accuracy | 0.562500 |
| Accepted links | 12 |
| True / false positive / false negative links | 10 / 2 / 5 |

Model bytes reproduce within each platform; repeated scores and resolution sets
match within each platform. Cross-platform dataset/splits/schema, resolution sets,
set quality and failure reports agree. Model binary equality across platforms is
not required. Each platform verified 18 manifests and 166 artifacts.

Feature schema: `73d1ae878bef3d6911bf29ce06ba20202a390d396c307bae3e7928a11ed74009`.

False negatives: retrieval 1, scoring 2, ownership 1, decoding 0, explicit ambiguity 1.
False positives: scoring 2, with zero in the other attribution stages. The ambiguity
is a declared shared-target label conflict. Stage counts follow policy precedence.


The [compact bundle](docs/evidence/PASS_B_RUNS.json) retains manifests,
physical hashes, producing source inventory, logical identities, environment and
resource observations. Full model/stage tables remain under
`outputs/neutral-current-pass-b-windows` and
`outputs/neutral-current-pass-b-linux`.

See [reproduction](docs/REPRODUCIBILITY.md) and
[usage](docs/PASS_B_USAGE.md) for commands and contract semantics.
