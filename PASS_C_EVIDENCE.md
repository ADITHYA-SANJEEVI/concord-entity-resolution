# Pass C: current synthetic evidence

Producing implementation: `0ead99612ce93d47e51d748d3ecc01a026a92864` (clean on both platforms).
Identity epoch: `concord.neutral-reference.v1`. These runs establish new source,
configuration, schema, model metadata and artifact lineage identities. Prior
bundles are superseded; changed bytes do not retain prior cryptographic identities.

All inputs are invented and publicly distributable. Results describe the declared
fixtures and workloads. They do not establish independent real-world quality.

## Research evaluation

The entity-disjoint plan contains 320 training, 64 calibration and 133 test queries.
Generator templates are shared. All 12 experiments use the same 59-column order,
exclusive target ownership and 0.640 decoder. Experiments remain diagnostic.

| Experiment | Macro precision | Macro recall | Macro F0.5 | Exact-set accuracy |
|---|---:|---:|---:|---:|
| k1 | 0.857143 | 0.917293 | 0.857143 | 0.857143 |
| logistic | 0.864662 | 0.924812 | 0.864662 | 0.864662 |
| logistic_seed7 | 0.864662 | 0.924812 | 0.864662 | 0.864662 |
| no_reverse | 0.842105 | 0.902256 | 0.842105 | 0.842105 |
| reference | 0.842105 | 0.894737 | 0.842105 | 0.842105 |
| transliterated_name | 0.842105 | 0.894737 | 0.842105 | 0.842105 |
| without_address | 0.842105 | 0.887218 | 0.839599 | 0.827068 |
| without_competition | 0.857143 | 0.924812 | 0.857143 | 0.857143 |
| without_cross_script | 0.842105 | 0.902256 | 0.842105 | 0.842105 |
| without_name | 0.842105 | 0.883459 | 0.838346 | 0.819549 |
| without_numeric | 0.842105 | 0.894737 | 0.842105 | 0.842105 |
| without_retrieval | 0.842105 | 0.902256 | 0.842105 | 0.842105 |

Logistic's paired macro F0.5 delta is +0.022556, with a descriptive
95% interval [-0.015038, +0.067669]. It includes zero;
no scorer winner is established on this fixture.


Paired bootstrap intervals, cohort deltas, calibration, structural risk versus
confidence comparisons and Failure Atlas counts are retained in the bundle.
Intervals describe the synthetic queries; shared targets/templates limit sampling
interpretation. No automatic promotion or threshold tuning is performed.

Reference held-out failure attribution:

| Policy stage | False negatives | False positives |
|---|---:|---:|
| AMBIGUOUS_OR_INSUFFICIENT_EVIDENCE | 1 | 0 |
| DECODING | 0 | 0 |
| OWNERSHIP | 0 | 0 |
| RETRIEVAL | 8 | 0 |
| SCORING | 5 | 7 |

## Robustness

Each perturbation reruns retrieval, graph features, scores, ownership and decoding
with the fitted reference. The original 133 queries define change denominators.
Added target competition also creates one additional query in its full quality report.

| Perturbation | Changed original queries | Change rate |
|---|---:|---:|
| case | 0 / 133 | 0.000000 |
| competition | 6 / 133 | 0.045113 |
| punctuation | 7 / 133 | 0.052632 |
| spacing | 11 / 133 | 0.082707 |
| token_order | 12 / 133 | 0.090226 |
| transliteration | 10 / 133 | 0.075188 |

Row permutation and repeated reference training/inference preserve resolution sets.
All three scale workloads also match dataset, candidate-count and resolution
identities across platforms.
Cross-platform logical decisions, set quality, policy attribution and robustness
query changes agree. Probability deltas are measured separately; general model-byte
or floating-point portability is not claimed. Capsules retain raw diagnostics.

## Scale and verification

The default scale recipe executed 128, 512 and 2,048 source-query workloads, with
one warmup and three measured repetitions per size, using the fitted reference.
Typed raw observations and the bundle retain per-stage timing, sampled process RSS,
throughput, candidate counts, artifact sizes and repeat resolution fingerprints.
Median measured pipeline times and maximum sampled process RSS follow:

| Platform | Queries | Candidates | Median seconds | Maximum sampled RSS (MiB) |
|---|---:|---:|---:|---:|
| windows | 128 | 2931 | 1.980 | 184.73 |
| windows | 512 | 11338 | 10.413 | 223.51 |
| windows | 2048 | 44559 | 73.578 | 369.07 |
| ubuntu_wsl | 128 | 2931 | 1.475 | 213.28 |
| ubuntu_wsl | 512 | 11338 | 8.037 | 264.34 |
| ubuntu_wsl | 2048 | 44559 | 75.444 | 421.93 |

Both platforms ran on the same host and their suites overlapped; these are uncontrolled
host observations. RSS includes dependencies and allocator state and can miss brief
peaks. Timing boundaries exclude imports, fixture generation, loading and serialization.

Each platform verified 412 public and 34 scale artifacts (446 total), the combined
artifact DAG, and all physical hashes.
Both complete test suites passed 211 tests. Eighteen feature/schema tests passed again
after the final serialization-description correction. Ruff, compileall and whitespace
checks passed. Retention rejects artifact tampering, dirty producers and missing source
inventory. The pre-existing native pytest warning and unrelated optional dependency
conflict are recorded in the bundle's validation notes.


The [compact bundle](docs/evidence/PASS_C_RUNS.json) retains manifests,
physical hashes, producing source inventory, logical identities, environment and
resource observations. Full model/stage tables remain under
`outputs/neutral-current-pass-c-windows` and
`outputs/neutral-current-pass-c-linux`.

See [reproduction](docs/REPRODUCIBILITY.md) and
[usage](docs/PASS_C_USAGE.md) for commands and contract semantics.
