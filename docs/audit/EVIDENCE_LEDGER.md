# Evidence Ledger: Concord Baseline Claims

**Repository:** `concord-entity-resolution`  
**Preserved Baseline Commit:** `1133bfda496e2be59623fe154ec3dac45c13361f`  
**Classification System:**
- **Class A (Directly Verified):** Code + preserved artifact/schema/configuration in Git directly support the claim.
- **Class B (Strongly Supported):** Reliable historical artifact, portal manifest, or output hash survives, but full re-execution from scratch is blocked by omitted private data or environment dependencies.
- **Class C (Historical Context):** Documented in preserved experiment logs, notes, or team history, but secondary primary evidence in Git is partial or unrecovered.
- **Class D (Newly Reproduced):** Reserved for new, controlled live reruns. *(Not used in this audit pass; no code was executed or modified).*
- **Class E (Aspirational):** Future architecture, planned experiments, or design goals only.

---

## 1. Primary Evidence Ledger

| CLAIM_ID | CLAIM DESCRIPTION | REPORTED VALUE | METRIC / UNIT | POPULATION / SPLIT | PRIMARY CODE / ARTIFACT LOCATION | EVIDENCE CLASS | CONFIDENCE | REPRODUCIBILITY STATUS | AUDIT NOTES & CORRECTED WORDING |
|---|---|---|---|---|---|---|---|---|---|
| **CLM-01** | Ordered feature schema feature count | 59 | Count | Production | `src/concord/legacy_amazon/artifacts/ordered_59_feature_schema.json` | **A** | VERY HIGH | Runnable Now | Directly verified by contract test `test_frozen_schema_contract`. 59 distinct float32 feature names. |
| **CLM-02** | Base vs cross-script feature split | 55 base + 4 cross-script | Count | Production | `src/concord/legacy_amazon/artifacts/ordered_59_feature_schema.json`, `frozen_stage1_55_scorer.py` | **A** | VERY HIGH | Runnable Now | 55 base features plus `f55`, `f56`, `f57`, `f58`. |
| **CLM-03** | LightGBM model configuration | 600 trees, lr=0.05, 63 leaves, L2=1.0 | Hyperparameters | Training | `src/concord/legacy_amazon/artifacts/lightgbm_config.json`, `frozen_stage1_55_scorer.py:196` | **A** | VERY HIGH | Runnable Now | Directly verified by `test_frozen_model_config_contract`. Notes `seed_recovery: DEFAULTED_TO_42_NO_PRIOR_VALUE_FOUND`. |
| **CLM-04** | Fixed acceptance threshold | 0.640 | Probability threshold | Production (S2, S3) | `run_pipeline.py:35`, `frozen_test_production.py:38`, `ordered_59_feature_schema.json` | **A** | VERY HIGH | Runnable Now | Pinned across source files; applies identically to S2 and S3 after global ownership. |
| **CLM-05** | Five sparse retrieval views | 5 views (name:5, compact:5, address:5, combined:10, reverse:8) | Retrieval top-K | Retrieval stage | `frozen_full_graph_builder.py:19`, `configs/amazon_ml_2026.yaml` | **A** | VERY HIGH | Runnable with private data | Bounded top-N sparse TF-IDF matrix multiplication with `sparse_dot_topn`. |
| **CLM-06** | Deterministic global target ownership | Score DESC, s1_id ASC | SQL Partition Rule | Post-scoring | `run_pipeline.py:267-280`, `frozen_test_production.py:537-542` | **A** | VERY HIGH | Runnable Now | Enforces at most one S1 owner per target using DuckDB `ROW_NUMBER()`. |
| **CLM-07** | Submission archive & output hashes | ZIP: `d0574aab...`<br>matching: `0153c2ad...`<br>candidate: `70916432...` | SHA-256 | Submission test set | `src/concord/provenance.py`, `archive_manifest/final_submission.json` | **A** | VERY HIGH | Runnable Now | Pinned in code; verified by `test_submission_identities_are_pinned`. |
| **CLM-08** | Legacy source code snapshot integrity | 10 files matched | SHA-256 | Historical codebase | `archive_manifest/source_snapshot.json` | **A** | VERY HIGH | Runnable Now | Verified by `test_historical_source_hashes` against preserved files. |
| **CLM-09** | Omitted model artifact identities | joblib: `c5b0e224...`<br>txt: `7c1797a7...` | SHA-256 | Model artifact | `archive_manifest/artifacts.json`, `docs/REPRODUCIBILITY.md` | **A** | VERY HIGH | Blocked (Model omitted) | Verified omitted model digests. Replay requires privately supplying these files. |
| **CLM-10** | Deterministic normalization transform | NFKD + strip combining + casefold | Transform | All records | `frozen_full_graph_builder.py:21:fold()` | **A** | VERY HIGH | Runnable Now | `fold()` is self-contained Python code in the repository. |
| **CLM-11** | Public leaderboard Macro F0.5 | 0.955136 | Macro F0.5 | Public Test (Leaderboard) | `archive_manifest/final_submission.json`, `docs/RESULTS.md` | **B** | HIGH | Blocked (Competition closed) | Preserved historical submission evidence. Not independently re-queried from a live portal. |
| **CLM-13** | Selected POLICY_DEV Macro F0.5 | 0.9593640004712406 | Macro F0.5 | POLICY_DEV split | `archive_manifest/final_submission.json`, `docs/RESULTS.md` | **B** | HIGH | Blocked (Private splits) | Preserved qualification report checkpoint. Verified calculation contract, unrerun locally. |
| **CLM-14** | Test Source-1 population | 1,732,544 | Count | Test S1 | `frozen_test_production.py:619`, `archive_manifest/final_submission.json` | **B** | HIGH | Blocked (Private test data) | Hardcoded integrity assertion in test orchestrator and output manifests. |
| **CLM-15** | Valid target universe count | 9,969,589 | Count | Test S2 + S3 | `archive_manifest/final_submission.json`, `docs/RESULTS.md` | **B** | HIGH | Blocked (Private test data) | Supported by submission manifests and validator checks. |
| **CLM-16** | Frozen candidate graph size | 87,934,151 | Candidate Pairs | Test candidate graph | `archive_manifest/final_submission.json`, `docs/RESULTS.md` | **B** | HIGH | Blocked (Private test data) | Supported by graph manifests and submission manifest. Correct scale interpretation: bounded reduction from enormous Cartesian space. |
| **CLM-17** | Accepted link count | 5,708,382 | Links | Test output | `archive_manifest/final_submission.json`, `docs/RESULTS.md` | **B** | HIGH | Blocked (Private test data) | Supported by finalizer completion manifests. |
| **CLM-18** | Empty Source-1 output rows | 100,939 | S1 Rows (Zero matches) | Test output | `archive_manifest/final_submission.json`, `docs/RESULTS.md` | **B** | HIGH | Blocked (Private test data) | Supported by validator output records. |
| **CLM-19** | Training candidate rows | 3,376,945 | Candidate Rows | MODEL_TRAIN | `archive_manifest/final_submission.json`, `docs/RESULTS.md` | **B** | HIGH | Blocked (Private train data) | Candidate rows utilized to fit the 59-feature LightGBM model. |
| **CLM-20** | POLICY_DEV TP / FP / FN | 9,826 / 162 / 757 | Counts | POLICY_DEV split | `archive_manifest/final_submission.json`, `docs/RESULTS.md` | **B** | HIGH | Blocked (Private splits) | Preserved confusion breakdown from qualification report. |
| **CLM-21** | Model refit probability delta | $\le 1.965 \times 10^{-11}$ | Max absolute error | POLICY_DEV split | `docs/REPRODUCIBILITY.md` | **B** | HIGH | Blocked (Private model/data) | Preserved record of refit verification comparing deterministic retrain to original. |
| **CLM-22** | Cross-script qualification gain | +0.00557259 (vs control 0.953791) | Delta Macro F0.5 | POLICY_DEV split | `docs/EXPERIMENT_LEDGER.md:#13` | **B** | MEDIUM-HIGH | Blocked (Private splits) | Preserved experiment-ledger evidence. Not newly reproduced during this pass. |
| **CLM-23** | V1 production public score | 0.887 | Macro F0.5 | V1 Public Submission | `docs/EXPERIMENT_LEDGER.md:#1` | **C** | MEDIUM | Historical Only | Output hash `a6f83e7c...` documented in ledger; raw files outside repo. |
| **CLM-24** | V1 hard-negative calibration score | 0.921033617 | Macro F0.5 | V1 Calibration Split | `docs/EXPERIMENT_LEDGER.md:#2` | **C** | MEDIUM | Historical Only | Model hash `643e5a34...` documented in ledger. |
| **CLM-25** | V2 55-feature MODEL_SELECT score | 0.95866281 | Macro F0.5 | MODEL_SELECT (15,113 S1) | `docs/EXPERIMENT_LEDGER.md:#8` | **C** | MEDIUM | Historical Only | Model selection result prior to cross-script addition. |
| **CLM-26** | Hybrid 63-feature experiment score | 0.95976645 | Macro F0.5 | POLICY_DEV split | `docs/EXPERIMENT_LEDGER.md:#14` | **C** | MEDIUM | Historical Only | Inconclusive bootstrap CI `[-0.00129, 0.00200]`; explicitly REJECTED. |
| **CLM-27** | Distribution shift (France in test) | Uncalibrated at train time | Categorical split | Test set | `docs/FAILURE_ANALYSIS.md`, `frozen_full_graph_builder.py:18` | **C** | HIGH | Verified in code | Training code partitions only US/India; test code dynamically processes France. |
| **CLM-28** | Production runtime and hardware profile | 32 workers, ~128 GB RAM, ~2.5 hrs | Resources | Production run | `README.md`, `docs/PIPELINE.md` | **C** | MEDIUM | Historical Only | Reported operational envelope for high-memory Linux instance. |
| **CLM-29** | Later pipeline result ~0.966 | ~0.966 | Macro F0.5 | Historical recollection | None in Git | **C** | UNVERIFIED | Unrecovered | Team recollection from post-submission branches. NOT repository-backed. |
| **CLM-30** | Peak RAM ~2.9 GiB | ~2.9 GiB | RSS Memory | Candidate generation | None in Git | **C** | UNVERIFIED | Unrecovered | Mentioned in prompt context; not found in any committed file or log. |
| **CLM-31** | Candidate volume 32.05M / 16.76M | ~32.05M raw / ~16.76M K=20 | Candidate Pairs | Intermediate experiment | None in Git | **C** | UNVERIFIED | Unrecovered | Unverified prompt recollection. Not in repository manifests. |
| **CLM-32** | Resolution Certificate / Self-Auditing | Structurally complete proof object | Architecture | Future Concord | `docs/FUTURE_CONCORD_ROADMAP.md` | **E** | N/A | Aspirational | Roadmap and architecture proposal only. |
| **CLM-33** | Reversible merge/split workflow | Entity versioning system | Feature | Future Concord | `docs/FUTURE_CONCORD_ROADMAP.md` | **E** | N/A | Aspirational | Future product direction. |
| **CLM-34** | S1-level stability-vs-confidence experiment | Fragility vs error predictor | Metric / Study | Planned C4 Gate | Architecture Freeze | **E** | N/A | Aspirational | Approved experimental study for C4 gate. |

---

## 2. Evidence Reconciliation Summary

- **Total Claims Audited:** 33
- **Class A (Directly Verified):** 10
- **Class B (Strongly Supported):** 11
- **Class C (Historical Context / Unrecovered):** 9
- **Class E (Aspirational / Future Design):** 3
- **Explicitly Downgraded / Unverified Prompt Figures:**
  - `~2.9 GiB` peak RAM (Downgraded to Class C / Unverified)
  - `32.05M / 16.76M` candidate run (Downgraded to Class C / Unverified)
  - `~0.966` later pipeline score (Downgraded to Class C / Unverified)
  - Scale multiplication wording $1.73\text{M} \times 9.97\text{M} = 87.9\text{M}$ (Corrected: bounded sparse reduction)
  - `+0.00558` cross-script gain (Classified as Class B historical ledger evidence, not newly reproduced)
