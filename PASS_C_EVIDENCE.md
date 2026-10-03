# Concord Pass C evidence

Pass C completes the bounded public C4 research layer over the accepted C1-C3 core. All results below were executed on invented P0 data. No challenger was promoted. Concord is the current individual project of Adithya Sanjeevi.

## Producer and reproduction

Implementation producer: `26b20dcf7a31666e44e2e5ae19a98d0c8e6cc24b` on `c4/challengers-stability-scale`, starting from `2773034633a4cbacd07bd7f69070a83add6d9df2`. Both platform public/scale manifests recorded `dirty=false`. This document and the compact bundle are retained by a subsequent evidence-only commit, avoiding self-reference.

```bash
python scripts/reproduce_pass_c.py --output outputs/pass-c-windows-clean
# Run the same script with Ubuntu Python and a separate output:
python scripts/reproduce_pass_c.py --output outputs/pass-c-linux-clean
python scripts/retain_pass_c_evidence.py --windows outputs/pass-c-windows-clean --linux outputs/pass-c-linux-clean --output docs/evidence/PASS_C_RUNS.json
```

See [usage and exact definitions](docs/PASS_C_USAGE.md) and [retained metadata](docs/evidence/PASS_C_RUNS.json). Generated models, Parquet, capsules and logs remain under the ignored artifact roots recorded in the bundle. A clone regenerates them; they are not shipped as weights or bulk data.

## Population and policy

Recipe `concord.p0.multilingual-c4.v1`: 1,575 invented entities, with 320 training, 64 calibration and 133 held-out test queries. Roles have disjoint entity identities and an explicit committed split plan. Test has 266 targets and 131 truth links. Calibration/test labels never enter training, hard-negative mining or candidate generation. Templates are shared across roles; this is a diagnostic integration workload, not independent real-world generalization evidence.

Dataset identity: `79f52a08c24c51456d095cdc053265658dee7956756a839ce54ae754e83cd68e`. Split-plan identity: `e9fcfbcff10d476218bb94c0565ff44250d2290edb54b9899f4afdc51f3641f2`. Feature schema remains the ordered C3 59-column schema. Every scorer uses global ownership (score DESC, S1 ID ASC) and owner AND score >= 0.640. No C1-C3 runtime implementation changed beyond CLI registration.

## Challengers and ablations

Logistic regression uses a training-only StandardScaler, C=1, liblinear, tolerance 1e-8, maximum 2,000 iterations and seed 42. Seed 7 is a separate sensitivity check. Six ablations zero meaningful groups at fit and score and retrain without reordering columns. K=1 and no reverse view are explicit bounded retrieval variants. The name-transliteration challenger adds a separately fitted top-five Unidecode name view; original provenance wins on overlap and rescued rows retain their actual view origin. The baseline five views remain intact.

All rows below use the same 133 held-out queries. Paired 95% intervals use 1,000 query-unit bootstrap resamples, seed 2026. Shared templates/targets and the small population limit statistical interpretation. Zero observed delta is not proof of equivalence.

| Experiment | Macro F0.5 | Precision | Recall | Exact set | F0.5 delta [95% interval] | FP / FN |
|---|---:|---:|---:|---:|---|---:|
| reference | 0.842105 | 0.842105 | 0.894737 | 0.842105 | reference | 7 / 14 |
| logistic | 0.864662 | 0.864662 | 0.924812 | 0.864662 | +0.022556 [-0.015038, +0.067669] | 8 / 10 |
| without_name | 0.838346 | 0.842105 | 0.883459 | 0.819549 | -0.003759 [-0.008772, +0.000000] | 7 / 17 |
| without_address | 0.839599 | 0.842105 | 0.887218 | 0.827068 | -0.002506 [-0.006266, +0.000000] | 7 / 16 |
| without_numeric | 0.842105 | 0.842105 | 0.894737 | 0.842105 | +0.000000 [+0.000000, +0.000000] | 7 / 14 |
| without_retrieval | 0.842105 | 0.842105 | 0.902256 | 0.842105 | +0.000000 [-0.022556, +0.022556] | 8 / 13 |
| without_competition | 0.857143 | 0.857143 | 0.924812 | 0.857143 | +0.015038 [-0.015226, +0.052632] | 9 / 10 |
| without_cross_script | 0.842105 | 0.842105 | 0.902256 | 0.842105 | +0.000000 [-0.022556, +0.022556] | 8 / 13 |
| k1 | 0.857143 | 0.857143 | 0.917293 | 0.857143 | +0.015038 [-0.022556, +0.060150] | 8 / 11 |
| no_reverse | 0.842105 | 0.842105 | 0.902256 | 0.842105 | +0.000000 [-0.045113, +0.045113] | 8 / 13 |
| transliterated_name | 0.842105 | 0.842105 | 0.894737 | 0.842105 | +0.000000 [+0.000000, +0.000000] | 7 / 14 |
| logistic_seed7 | 0.864662 | 0.864662 | 0.924812 | 0.864662 | +0.022556 [-0.015038, +0.067669] | 8 / 10 |

Logistic has a higher point estimate, but its paired interval includes zero. No scorer winner is established. Removing competition has a positive point estimate with an interval including zero. Removing name/address slightly worsens this fixture. Several other ablations have zero aggregate delta, sometimes with different error locations. Full cohort deltas, calibration, resource observations and failure-stage movements are retained in the bundle and original reports.

| Retrieval | Candidates | Change | Overall truth recall | Cross-script truth recall (40 links) |
|---|---:|---:|---:|---:|
| reference | 2861 | 0 | 0.938931 | 0.800000 |
| k1 | 254 | -2607 | 0.938931 | 0.800000 |
| no_reverse | 1769 | -1092 | 0.938931 | 0.800000 |
| transliterated_name | 2932 | +71 | 0.938931 | 0.800000 |

The transliterated view adds candidate cost without recall/F0.5 benefit here. K=1 has much lower candidate cost with equal truth recall on this fixture; it is not a general retrieval recommendation. Both cross-script signals and original name/address/numeric/context signals overlap in information, so ablations are not causal contribution estimates.

## Robustness, reproducibility and drift

Each perturbation changes only S1 raw inputs and reruns the complete frozen-model pipeline, including candidate generation and graph features. Targets and existing truth stay fixed. The denominator is always the original 133 queries; competition adds one query to its full quality report.

| Perturbation | Changed original queries | Change rate |
|---|---:|---:|
| case | 0 / 133 | 0.0000% |
| spacing | 11 / 133 | 8.2707% |
| punctuation | 7 / 133 | 5.2632% |
| token_order | 12 / 133 | 9.0226% |
| transliteration | 10 / 133 | 7.5188% |
| competition | 6 / 133 | 4.5113% |

Row-order permutation actually reran retrieval/features/inference and reproduced scores/sets exactly within each platform. Repeated reference fitting/inference also matched within each platform. Logistic seeds 42 and 7 changed 0/133 test decisions. Formatting sensitivity is an observed limitation of the complete pipeline, despite deterministic normalization. The reference is preserved, so these findings do not silently change its policy.

Raw profiles compare missingness, Unicode name families, lengths/countries, candidate density, lane usage, retrieved-pair calibration and failure-stage mixtures. No distance threshold, causal drift explanation or universal stability label is introduced. The invented `P0-OOD` label is not a real country-generalization test.

The predeclared structural risk combines accepted lane counts, ownership/threshold margins and ambiguity. Main confidence is one minus minimum accepted score, with explicitly defined zero-match confidence from top rejected score or zero when no candidates. Four individual confidence baselines and zero/nonempty cohorts are also retained.

| Error-risk diagnostic (133 queries; 21 exact-set errors) | AUROC | AUPRC | Risk at 90% | Risk at 95% |
|---|---:|---:|---:|---:|
| confidence | 0.575043 | 0.371278 | 0.133333 | 0.133858 |
| structure | 0.907526 | 0.695711 | 0.083333 | 0.133858 |

Structure minus confidence AUROC: +0.332483, paired 95% interval [0.120292620670213, 0.5541701173222912]; AUPRC delta +0.324432, interval [0.09905261123250322, 0.5133601795481333]. Five hundred paired resamples give `descriptive improvement` on this synthetic population. Missing-candidate failures and the zero-match convention strongly affect these diagnostics. This is not a general claim that stability predicts real-world errors better than confidence. Full risk-coverage curves remain in the hashed original study artifact.

Individual baselines use their defined subsets, not an imputed full-population score. Top/minimum score and gap are inverted into risk; best rejected score is used directly.

| Baseline / subset | Queries | Errors | Confidence AUROC | Confidence AUPRC | Structure minus baseline AUROC interval |
|---|---:|---:|---:|---:|---|
| best_rejected_score | 124 | 13 | 0.7484407484407485 | 0.3970172388832942 | [0.02744286174150976, 0.2273142000643811] |
| minimum_accepted_score | 116 | 7 | 0.9148099606815203 | 0.2917989417989418 | [-0.25328113159888865, -0.035714285714285636] |
| score_gap | 124 | 13 | 0.891891891891892 | 0.36240757414020763 | [-0.10825198107806797, 0.03915083395958054] |
| top_candidate_score | 124 | 13 | 0.9601524601524601 | 0.7530358945055895 | [-0.17563548218029343, -0.029318796259362758] |
| nonempty | 116 | 7 | 0.9148099606815203 | 0.2917989417989418 | [-0.25328113159888865, -0.035714285714285636] |
| zero_match | 17 | 14 | 0.27380952380952384 | 0.7537515006002401 | [-0.08333333333333336, 0.2857142857142857] |

The result is mixed: structure improves on the composite full-population baseline,
but performs worse than top-score and minimum-accepted-score confidence on their
defined subsets. Score-gap and zero-match comparisons show no clear advantage.
Different denominators and missing-candidate cases explain why these findings must
remain separate; there is no universal superiority claim.

## Cohort results

Reference held-out metrics follow. Cohorts overlap; sizes are query counts. Challenger comparisons use reference membership for paired cohort differences, avoiding a moving denominator for diagnostic buckets.

| Cohort | Queries | F0.5 | Precision | Recall | Exact set |
|---|---:|---:|---:|---:|---:|
| address_missing_or_empty | 25 | 0.680000 | 0.680000 | 0.680000 | 0.680000 |
| address_present | 108 | 0.879630 | 0.879630 | 0.944444 | 0.879630 |
| competition_gt8 | 120 | 0.916667 | 0.916667 | 0.966667 | 0.916667 |
| competition_le8 | 13 | 0.153846 | 0.153846 | 0.230769 | 0.153846 |
| country:P0-OOD | 16 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| country:P0-SEEN | 117 | 0.820513 | 0.820513 | 0.880342 | 0.820513 |
| cross_script | 40 | 0.800000 | 0.800000 | 0.800000 | 0.800000 |
| name_missing_or_empty | 9 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| name_present | 124 | 0.830645 | 0.830645 | 0.887097 | 0.830645 |
| ownership_margin_gt001 | 116 | 0.939655 | 0.939655 | 1.000000 | 0.939655 |
| ownership_margin_undefined | 17 | 0.176471 | 0.176471 | 0.176471 | 0.176471 |
| retrieved_by:address | 108 | 0.879630 | 0.879630 | 0.944444 | 0.879630 |
| retrieved_by:combined | 124 | 0.895161 | 0.895161 | 0.951613 | 0.895161 |
| retrieved_by:compact | 116 | 0.887931 | 0.887931 | 0.948276 | 0.887931 |
| retrieved_by:name | 116 | 0.887931 | 0.887931 | 0.948276 | 0.887931 |
| retrieved_by:reverse | 124 | 0.895161 | 0.895161 | 0.951613 | 0.895161 |
| same_script_or_no_truth | 93 | 0.860215 | 0.860215 | 0.935484 | 0.860215 |
| truth_multi | 8 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| truth_single | 115 | 0.878261 | 0.878261 | 0.878261 | 0.878261 |
| truth_zero | 10 | 0.300000 | 0.300000 | 1.000000 | 0.300000 |

The cross-script cohort has 40 queries, including intentionally unretrievable cases; the complement includes same-script, unknown-script and zero-truth queries. No accepted reference owner margin <=0.01 was observed, so that empty bucket supplies no evidence. Small groups such as multi-truth (8) and missing name (9) cannot establish subgroup superiority.

## Current scale characterization

Observed host CPU: AMD Ryzen 5 5500U with Radeon Graphics, 6 cores / 12 logical CPUs (native CIM and Ubuntu lscpu). Ubuntu was actual WSL2, Ubuntu 24.04.4 LTS; it is not a controlled cross-platform hardware comparison. Exact OS, Python, package versions, available RAM, total RAM and source hashes are retained in the manifests. Model and retrieval use one thread; one additional RSS sampling thread is used.

One warmup and three measured repetitions per size. Stage timers cover normalization through evidence; pipeline includes sampler bookkeeping. Fixture creation, imports, model loading, GC and artifact serialization are excluded. Peak values below are maximum sampled process RSS at 10ms plus stage endpoints; they include dependencies and allocator state, can miss short spikes, and are not isolated stage allocations or OS high-water marks. Prior product objects are released between repetitions/sizes. Timings and model bytes are not required to match across platforms.

| Platform | Queries / targets | Candidate pairs | Pipeline median [min,max] seconds | Queries/s | Sampled maximum MiB | Retained stage bytes |
|---|---:|---:|---|---:|---:|---:|
| ubuntu_wsl | 128 / 264 | 2931 | 2.087 [2.014, 2.247] | 61.32 | 213.5 | 360,327 |
| ubuntu_wsl | 512 / 1056 | 11338 | 10.153 [9.616, 14.710] | 50.43 | 264.0 | 1,242,584 |
| ubuntu_wsl | 2048 / 4224 | 44559 | 89.522 [80.811, 101.212] | 22.88 | 414.1 | 4,487,563 |
| windows | 128 / 264 | 2931 | 1.537 [1.489, 1.580] | 83.25 | 183.8 | 360,319 |
| windows | 512 / 1056 | 11338 | 6.668 [6.644, 7.006] | 76.79 | 223.8 | 1,242,584 |
| windows | 2048 / 4224 | 44559 | 60.661 [57.190, 64.180] | 33.76 | 365.6 | 4,487,564 |

Measured stage medians and ranges (seconds):

| Platform / queries | Stage | Median | Min | Max |
|---|---|---:|---:|---:|
| ubuntu_wsl / 128 | normalization | 0.010 | 0.010 | 0.013 |
| ubuntu_wsl / 128 | retrieval | 0.245 | 0.217 | 0.349 |
| ubuntu_wsl / 128 | features | 1.302 | 1.287 | 1.389 |
| ubuntu_wsl / 128 | scoring | 0.212 | 0.202 | 0.265 |
| ubuntu_wsl / 128 | ownership | 0.029 | 0.025 | 0.036 |
| ubuntu_wsl / 128 | decoding | 0.029 | 0.027 | 0.032 |
| ubuntu_wsl / 128 | evidence | 0.205 | 0.180 | 0.272 |
| ubuntu_wsl / 512 | normalization | 0.047 | 0.038 | 0.067 |
| ubuntu_wsl / 512 | retrieval | 1.079 | 1.079 | 1.093 |
| ubuntu_wsl / 512 | features | 6.329 | 6.062 | 10.582 |
| ubuntu_wsl / 512 | scoring | 0.994 | 0.855 | 1.088 |
| ubuntu_wsl / 512 | ownership | 0.274 | 0.255 | 0.433 |
| ubuntu_wsl / 512 | decoding | 0.214 | 0.167 | 0.279 |
| ubuntu_wsl / 512 | evidence | 1.262 | 0.857 | 1.406 |
| ubuntu_wsl / 2048 | normalization | 0.204 | 0.156 | 0.226 |
| ubuntu_wsl / 2048 | retrieval | 4.548 | 3.758 | 4.924 |
| ubuntu_wsl / 2048 | features | 69.923 | 61.692 | 73.401 |
| ubuntu_wsl / 2048 | scoring | 3.178 | 3.100 | 6.560 |
| ubuntu_wsl / 2048 | ownership | 0.601 | 0.599 | 0.961 |
| ubuntu_wsl / 2048 | decoding | 2.317 | 2.117 | 3.265 |
| ubuntu_wsl / 2048 | evidence | 9.378 | 8.346 | 12.252 |
| windows / 128 | normalization | 0.011 | 0.010 | 0.016 |
| windows / 128 | retrieval | 0.154 | 0.154 | 0.171 |
| windows / 128 | features | 0.865 | 0.859 | 0.929 |
| windows / 128 | scoring | 0.243 | 0.212 | 0.304 |
| windows / 128 | ownership | 0.030 | 0.026 | 0.039 |
| windows / 128 | decoding | 0.027 | 0.027 | 0.029 |
| windows / 128 | evidence | 0.161 | 0.157 | 0.177 |
| windows / 512 | normalization | 0.040 | 0.040 | 0.043 |
| windows / 512 | retrieval | 0.686 | 0.681 | 0.707 |
| windows / 512 | features | 3.998 | 3.799 | 4.075 |
| windows / 512 | scoring | 0.873 | 0.862 | 0.917 |
| windows / 512 | ownership | 0.161 | 0.110 | 0.207 |
| windows / 512 | decoding | 0.236 | 0.193 | 0.273 |
| windows / 512 | evidence | 0.816 | 0.733 | 0.866 |
| windows / 2048 | normalization | 0.168 | 0.167 | 0.185 |
| windows / 2048 | retrieval | 3.250 | 3.134 | 3.264 |
| windows / 2048 | features | 41.068 | 39.539 | 45.720 |
| windows / 2048 | scoring | 3.616 | 3.517 | 4.430 |
| windows / 2048 | ownership | 0.472 | 0.466 | 0.542 |
| windows / 2048 | decoding | 1.691 | 1.645 | 1.750 |
| windows / 2048 | evidence | 9.250 | 8.583 | 9.566 |

Feature computation dominates the largest workload; evidence and decoding also grow faster than query count in this implementation. This records a present performance limit, not a production-throughput claim or extrapolation to the historical Amazon corpus. Raw measurements are typed Parquet; logical resolution fingerprints repeat within every workload. Full stage RSS, throughput, candidate counts and artifact sizes are retained in metadata.

## Failure Atlas

Reference test has 7 false positives and 14 false negatives. The earliest C3 policy gates attribute 8 FN to retrieval, 5 FN to scoring, 1 FN to explicit ambiguity, and all 7 FP to scoring. Reference ownership/decoding counts are zero; ownership failures do occur in no-reverse and retrieval-feature-ablation runs. No decoding failure was manufactured to fill a category. All experiment/calibration/test and perturbation atlas rows are generated from actual outputs.

The earliest scoring attribution can precede ownership loss: for example the losing ownership query also falls below the decoder threshold. Atlas rows include source/truth/final sets, complete candidate counts, top-eight scored candidates plus the attributed pair when retrieved, actual lane provenance, owners, decoder dispositions and margins. Full bulk stages are retained separately. This is policy-stage attribution, not causal root-cause analysis.

Representative generated reference cases:

| Query / target | Error | Policy stage | Candidates |
|---|---|---|---:|
| test-amb-z / test-amb-target | FALSE_NEGATIVE | AMBIGUOUS_OR_INSUFFICIENT_EVIDENCE | 2 |
| test-own-a / test-own-target | FALSE_POSITIVE | SCORING | 2 |
| test-own-z / test-own-target | FALSE_NEGATIVE | SCORING | 2 |
| test-q-0006 / test-t-0006 | FALSE_POSITIVE | SCORING | 63 |
| test-q-0015 / test-t-0015 | FALSE_NEGATIVE | RETRIEVAL | 0 |
| test-q-0031 / test-t-0031 | FALSE_NEGATIVE | RETRIEVAL | 0 |
| test-q-0060 / test-t-0060 | FALSE_NEGATIVE | SCORING | 25 |

## Validation and lineage

| Platform | Full suite | Ruff | compileall | Public reproduction | Verified artifacts |
|---|---|---|---|---|---:|
| ubuntu_wsl, Python 3.12.3 | 215 passed (581.75s) | PASS | PASS | public + scale COMPLETED | 446 |
| windows, Python 3.12.10 | 215 passed (555.42s) | PASS | PASS | public + scale COMPLETED | 446 |

Commands: `python -m pytest -q`; `python -m ruff check src/concord --exclude legacy_amazon tests scripts examples/synthetic/pass_b_fixture.py`; `python -m compileall -q src/concord tests scripts examples/synthetic/pass_b_fixture.py`; `git diff --check`; and the reproduction script. Native used `.venv/Scripts/python.exe`; Ubuntu used `/var/tmp/concord-pass-a-closure-venv/bin/python` against the workspace mounted under `/mnt/c`. The pre-existing native pytest-asyncio deprecation warning remains. Final native pytest returned explicit native exit code zero.

Development tests exposed and corrected C4 float32 scaler inference and row-order-dependent competitor selection; a development scale run exposed copied-model self-parent lineage. The final full suites passed after correction. These were C4 defects; no C1-C3 correctness defect or semantic fix was required.

Both platform runs verified every physical artifact hash and byte length. The retained bundle contains the producing manifests, artifact roots, full artifact identities/parents, environment/source hashes, compact measured reports, log hashes and manifest-file hashes. Joint public/scale DAG validation connects consumed models back to train features/mined labels/definitions, then retrieval/features/scores/ownership/dispositions/sets/capsules/atlas and evaluations. Source bytes match the implementation producer. A narrow verification-only corrective commit, recorded in the bundle, distinguishes logical attribution from raw numeric diagnostics; the benchmark/scorer sources and retained producing identities remain unchanged. Both final full suites include the two comparison regressions.

Across 12 experiments and both calibration/test populations, resolution sets, set quality and logical failure attribution matched across platforms. Scored graphs matched. Logistic probabilities differed by at most 7.037556093436592e-10, including corresponding score/margin diagnostics in Failure Atlas reports; all LightGBM variants were within the recorded diagnostic 1e-12 comparison. Actual maximum deltas and exact score-hash equality flags are retained without imposing universal probability equality. Robustness changed-query sets matched. This is observed fixture equivalence, not a universal model-binary or timing portability guarantee. CI now configures Pass C on Windows/Ubuntu, but no remote CI execution is claimed.

## Preservation, claim boundary and conclusion

Zero diff to `src/concord/legacy_amazon/**`, `archive_manifest/**`, `tests/test_preserved_contract.py`, `tests/test_manifests.py`, and frozen Pass A/B evidence. The accepted Pass B tag is unchanged. Original opaque legacy identifiers remain intact. No private data, model weights, Parquet, logs, temporary files, environments or caches are staged.

Historical Amazon public F0.5 0.955136 and the bounded 87.9M-pair graph over 1.73M sources / 9.97M targets remain historical evidence. Current C1-C4 public results and current scale results are separate. No private data/model/probability/capped-sampling parity, rank 2502, unrecovered 0.966 result, WDC performance or production-throughput claim is made.

C1-C4 now form a complete public P0 core with bounded retrieval, fixed reference inference, typed evidence, evaluation, diagnostic challengers, robustness and measured scale. Optional WDC/Ditto/Splink/adaptive-K experiments were cut to complete the mandatory suite. Larger, independent multilingual and real-world datasets remain necessary for generalization or promotion. No C5, frontend, inspection API, push, merge or release/tag was performed.

The verified COMPLETED runs and typed evidence are suitable inputs for a future read-only inspection API and Resolution Explorer. That future work still needs artifact retention, pagination and user-facing inspection design; it is not implemented here.
