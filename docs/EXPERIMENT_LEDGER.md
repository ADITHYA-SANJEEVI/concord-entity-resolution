# Experiment ledger

This ledger preserves 24 meaningful experiment groups. It summarizes evidence without copying generated datasets, feature matrices, caches, or model weights. Paths refer to the original workspace at `C:\Users\adith\Downloads\6ab10eb3b23ba_student_resource`.

## Status key

- PROMOTED: contributed to the preserved 0.955136 submission.
- REJECTED: completed or qualified, but did not pass its promotion rule.
- DIAGNOSTIC: produced useful evidence without defining a promoted replacement.
- LATER EXPERIMENT: ran after the selected submission and did not contribute to it.

## 1. Original V1 production

- Chronology: September 25 to 26, 2026.
- Question: Could a first end-to-end sparse candidate and classifier pipeline produce a valid large-scale submission?
- Code and artifacts: `build_v1_submission.py`, `calibrate_v1_submission.py`, `experiments/generation_01/v1_submission_01/`.
- Strategy: earlier 35,456,200-pair graph, original histogram-gradient-boosting fallback, hard-negative model, source-specific calibrated thresholds, and global target uniqueness.
- Data: threshold calibration followed by full test inference.
- Verified result: public Macro F0.5 0.887. Primary output hash `a6f83e7cd4f2962be37a5274347b8b118972c53b5ba81d8c4d6409afda8361b2`.
- Disposition: REJECTED as the final baseline; preserved as the first complete production lineage.
- Lesson: end-to-end execution and validation worked, but retrieval depth and cross-script performance left substantial quality headroom.

## 2. V1 hard-negative reranker

- Chronology: September 25 to 26.
- Question: Would targeted hard negatives improve the original pair classifier?
- Code and artifacts: `hard_negative_k20_reranker_poc.py`, `experiments/generation_01/hard_negative_reranker_poc_01/`, V1 submission report.
- Strategy: hard-negative retraining over the earlier candidate graph.
- Data: labeled training and threshold-calibration cohorts.
- Verified calibration result: Macro F0.5 0.9210336170316877 under its selected policy; model hash `643e5a341e74dd7affc653de53059f7a2052a593e82da3cdb0c8fb65c3844d6f`.
- Disposition: PROMOTED within V1, later superseded by the five-view 55/59-feature system.
- Lesson: harder negatives improved V1, but later direct hard-negative retraining on the stronger feature stack did not repeat the gain.

## 3. Decision-policy and structured-decoder studies

- Chronology: September 25 to 26.
- Question: How should pair scores become zero, one, or many links under target uniqueness?
- Code and artifacts: `v1_decision_policy.py`, `decision_policy_diagnostic.py`, `structured_set_decoder_poc.py`, `experiments/generation_01/v1_decision_policy_01/`, `decision_policy_diagnostic_01/`, `structured_decoder_poc_01/`, and `decoder_policy_poc_01/`.
- Strategy: source thresholds, set decoding, cardinality diagnostics, and global ownership.
- Data: calibration and model-selection splits.
- Verified result: global target ownership with deterministic tie-breaking remained the stable policy family; more elaborate decoders were not selected.
- Disposition: DIAGNOSTIC, with ownership logic carried forward.
- Lesson: policy quality is separate from pair ranking quality and must be evaluated on final per-S1 sets.

## 4. Blocking parity causal analysis

- Chronology: September 26.
- Question: Would production-scale posting behavior improve parity with the intended blocker?
- Code and artifacts: `experiments/generation_01/blocking_parity_causal_01/`.
- Strategy: causal comparison of baseline and parity-corrected blocking on a fixed evaluation cohort.
- Data: labeled calibration population; raw test files were not read in the experiment.
- Verified result: Macro F0.5 fell from 0.921033617032 to 0.894473956476; oracle fell by 0.034087109477.
- Disposition: REJECTED.
- Lesson: greater structural parity or candidate volume does not guarantee better candidate quality.

## 5. Query-scope sharding qualification

- Chronology: September 26.
- Question: Could deeper shard-local retrieval recover cap-suppressed truths within the deadline?
- Code and artifacts: `experiments/query_scope_sharding_qualification_01/`.
- Strategy: selected US and India shards with deeper K=20 retrieval.
- Data: 735 selected calibration Source-1 records.
- Verified result: selected-cohort F0.5 improved by 0.027706738411, but projected production runtime was 46.961 hours before safety margin and France quality was unknown.
- Disposition: REJECTED on operational and generalization grounds.
- Lesson: a positive small-cohort result can still be unsuitable for production scale.

## 6. Target-competition LightGBM challenger

- Chronology: September 26.
- Question: Could target-competition features improve V1 ownership decisions?
- Code and artifacts: `experiments/target_comp_lgbm_01/`.
- Strategy: LightGBM challenger with target-component evidence.
- Data: frozen V1 model-selection cohort.
- Verified result: F0.5 improved from 0.921636542 to 0.933356696, but the required 10,000-component bootstrap was not feasible in the bounded run.
- Disposition: REJECTED by the predeclared confidence gate.
- Lesson: point improvement without the required uncertainty evidence was not enough to deploy.

## 7. Five-view sparse retrieval qualification

- Chronology: September 26 to 27.
- Question: Could complementary sparse views close the V1 retrieval ceiling efficiently?
- Code and artifacts: `run_ayan_retrieval_01.py`, `run_ayan_retrieval_light_01.py`, `experiments/ayan_retrieval_01/`, `ayan_retrieval_light_01/`, `ayan_retrieval_light_02/`, and `ayan_retrieval_full_01/`.
- Strategy: name, compact-name, address, combined, and reverse-combined TF-IDF views.
- Data: small and medium qualification samples followed by full graph production.
- Verified sample result: medium oracle 0.999622554 and truth recall 0.999136293 on 5,000 Source-1 records; 121 truths came from the reverse-only view.
- Disposition: PROMOTED.
- Lesson: heterogeneous sparse views produced a large recall improvement while remaining computationally tractable.

## 8. Frozen 55-feature Stage-1 scorer

- Chronology: September 27.
- Question: How far could the five-view graph go with direct, rank, and graph-context features?
- Code and artifacts: `frozen_stage1_55_scorer.py`, `frozen_test_production.py`, `experiments/ayan_retrieval_full_01/stage1_55/`.
- Strategy: 55 float32 features and LightGBM, followed by global ownership and 0.64 policy.
- Data: 91,621,656 training/model-selection graph edges in qualification; frozen test graph in later production.
- Verified model-selection result: Macro F0.5 0.95866280972158 on 15,113 Source-1 records, below that branch's 0.98 authorization threshold.
- Disposition: PROMOTED as the base architecture and test candidate graph, but not as the final 55-feature classifier.
- Lesson: exact graph-context features were valuable; residual errors were concentrated in cross-script and ranking cases.

## 9. XGBoost ranker challenger

- Chronology: September 26.
- Question: Could pairwise ranking improve truth ordering over the V1 hard-negative classifier?
- Code and artifacts: `experiments/generation_01/xgbranker_kaggle_01/`.
- Strategy: GPU XGBRanker with 34 engineered features and a separately qualified native threshold policy.
- Data: model-selection ranking diagnostic and POLICY_DEV policy evaluation.
- Verified result: action-oracle F0.5 improved from 0.972663469 to 0.975471162, but the native POLICY_DEV threshold policy scored 0.908267798 versus V1's 0.916242506.
- Disposition: REJECTED.
- Lesson: improved ordering did not translate into a better final decision policy.

## 10. Qwen semantic reranker probe

- Chronology: September 25 to 26.
- Question: Did a multilingual semantic model contain corrective signal for hard ranking inversions?
- Code and artifacts: `qwen3_semantic_reranker_poc.py`, `build_qwen3_kaggle_package.py`, `experiments/generation_01/qwen3_semantic_reranker_poc_01/`, and `qwen3_kaggle_gpu_01/`.
- Strategy: Qwen3 embedding/reranking probe over selected difficult pairs.
- Data: 755 unique probe pairs.
- Verified result: 172 inversions fixed, 128 still wrong, six control regressions, and 0.519 pairs per second in the local probe.
- Disposition: DIAGNOSTIC, not part of the final submission.
- Lesson: semantic signal existed, especially for cross-script pairs, but the measured local path was too narrow and slow to establish an end-to-end production gain.

## 11. Direct hard-negative challenger on the 55-feature stack

- Chronology: September 27.
- Question: Would new hard-negative construction improve the banked 55-feature model?
- Code and artifacts: `experiments/codex3_direct_0950_feature_challenger_01/`.
- Strategy: one genuinely new feature lane plus hard-negative retraining.
- Data: POLICY_DEV; test and final holdout were not accessed.
- Verified result: F0.5 fell from 0.9537914070796608 to 0.9495816085460622, delta -0.004209798533598597.
- Disposition: REJECTED.
- Lesson: reducing one false-over-truth inversion did not compensate for broader regressions.

## 12. Model2Vec semantic fusion

- Chronology: September 27.
- Question: Could compact multilingual embeddings add semantic evidence to the frozen scorer?
- Code and artifacts: `experiments/model2vec_fusion_preflight_staging/`.
- Strategy: Model2Vec features and a fixed semantic fusion qualification.
- Data: frozen training and POLICY_DEV candidate populations.
- Verified result: the experiment reported a positive semantic qualification but was classified as too small for the radical replacement lane; no test scoring was authorized.
- Disposition: REJECTED for production, retained as semantic evidence.
- Lesson: small development gains require a deployment-sized effect and stable confidence before replacing a simpler baseline.

## 13. Four-feature cross-script model

- Chronology: September 27, before selected test production.
- Question: Could deterministic transliteration and script-aware features improve the 55-feature model?
- Code and artifacts: `qualified_crossscript_generator.py`, `experiments/asmi_crossscript_local_01/`, and `asmi_crossscript_test_production_01/`.
- Strategy: append transliterated name Jaccard, maximum original/transliterated name ratio, dominant-script mismatch, and transliterated address Jaccard.
- Data: the same 3,376,945 training candidate rows and frozen POLICY_DEV split.
- Verified result: POLICY_DEV Macro F0.5 0.9593640004712406, gain 0.005572593391579783 over the recorded control.
- Disposition: PROMOTED and used by the preserved submission.
- Lesson: compact deterministic cross-script features delivered a verified gain without a runtime network or large semantic model dependency.

## 14. Hybrid 63-feature study

- Chronology: September 27.
- Question: Would four semantic features improve the 59-feature cross-script model?
- Code and artifacts: `experiments/hybrid_63_local_01/` and the hybrid result in `asmi_crossscript_local_01/`.
- Strategy: combine the 59 frozen features with four semantic features.
- Data: POLICY_DEV.
- Verified result: Macro F0.5 0.9597664453082749, but the paired bootstrap interval versus cross-script was [-0.0012880004355121848, 0.002000169144812192].
- Disposition: REJECTED as inconclusive.
- Lesson: a higher point estimate did not establish a reliable improvement.

## 15. Embedding interaction verifier

- Chronology: September 27.
- Question: Could learned interactions between paired embeddings correct a narrow set of ownership errors?
- Code and artifacts: `experiments/codex5_embedding_interaction_verifier_01/`.
- Strategy: elementwise product and absolute difference embeddings, logistic verifier, then fixed LightGBM fusion.
- Data: frozen raw-score top pairs plus semantic-selected owner edges on POLICY_DEV.
- Verified result: reported gain versus semantic was 0.0014155915533270447, with a bootstrap interval crossing zero.
- Disposition: REJECTED as too small and uncertain; test was not accessed.
- Lesson: targeted verifiers need clear incremental value after the strong cross-script baseline.

## 16. Triadic coherence and sequential decision studies

- Chronology: September 27.
- Question: Could query-target-rival coherence or sequential stopping improve set decisions?
- Code and artifacts: `experiments/codex6_triadic_coherence_01/`, `codex11_sequential_stopping_01/`, and `c12_prefix_utility_regression_01/`.
- Strategy: query-level and prefix-level meta decisions over frozen scores.
- Data: frozen training and POLICY_DEV decisions.
- Verified result: no branch produced a promoted policy in the preserved lineage.
- Disposition: REJECTED or DIAGNOSTIC.
- Lesson: added decision complexity did not demonstrate a stable improvement over global ownership and a fixed threshold.

## 17. Zero-match abstention

- Chronology: September 27.
- Question: Could a conservative query classifier suppress false-positive sets for true zero-match records?
- Code and artifacts: `experiments/codex6_zero_match_abstention_01/`.
- Strategy: fixed 35-feature LightGBM query classifier with a frozen high-confidence abstention threshold.
- Data: 65,475 training Source-1 records and POLICY_DEV.
- Verified result: Macro F0.5 0.9560014805765151, exactly unchanged from its semantic baseline because every fired case was already empty.
- Disposition: REJECTED as a null result.
- Lesson: a precise auxiliary detector adds no value when its actions are redundant with the existing policy.

## 18. Top-50 multilingual cross-encoder

- Chronology: September 27.
- Question: Could a pretrained multilingual cross-encoder replace frozen pair scores on the highest-ranked candidates?
- Code and artifacts: `experiments/codex6_top50_crossencoder_01/`.
- Strategy: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` over 18,628 POLICY_DEV rerank pairs.
- Data: 409,846 training pairs and POLICY_DEV.
- Verified result: Macro F0.5 0.9442189412135295, delta -0.011782539362985678 versus the semantic baseline, with a fully negative bootstrap interval.
- Disposition: REJECTED; no test scoring.
- Lesson: a licensed pretrained model can still be materially worse on the final task policy.

## 19. India oracle-rescue analysis

- Chronology: September 27.
- Question: Could deeper retrieval selectively recover India truths missed by the frozen graph?
- Code and artifacts: `policy_dev_oracle_autopsy.py`, `experiments/codex4_india_oracle_rescue_01/`, and `c9_oracle_gap_decomposition_01/`.
- Strategy: gate India rows with low forward-channel agreement, then deepen forward retrieval.
- Data: model-selection oracle analysis and POLICY_DEV gate-rate checks; test was not run.
- Verified result: 94 additional truth links recovered in oracle analysis and relaxed F0.5 increased by 0.0005645212319251858, with an estimated 19,093,608 new test edges.
- Disposition: DIAGNOSTIC, not included in the selected submission.
- Lesson: retrieval misses remained, but the projected incremental graph was large relative to the small oracle gain.

## 20. Cardinality-prefix model

- Chronology: September 27.
- Question: Could a learned target count choose a better prefix of owned candidates per Source-1 record?
- Code and artifacts: `experiments/c8_cardinality_prefix_01/`.
- Strategy: learned cardinality and prefix selection over frozen cross-script owner ordering.
- Data: POLICY_DEV.
- Verified result: Macro F0.5 0.9568156187486161, delta -0.0025483817226245042; exact K accuracy 0.8471211118464593.
- Disposition: REJECTED.
- Lesson: useful count prediction accuracy did not improve the final precision-weighted metric.

## 21. Expected-F0.5 decision rule

- Chronology: September 27.
- Question: Could calibrated expected utility select a better candidate set than a fixed pair threshold?
- Code and artifacts: `experiments/codex7_expected_f05_decision_01/`.
- Strategy: five-fold out-of-fold isotonic calibration and exact expected-F0.5 prefix evaluation.
- Data: model train and POLICY_DEV.
- Verified result: Macro F0.5 0.9581595027871037, delta -0.0012044976841368848.
- Disposition: REJECTED.
- Lesson: mathematically exact utility optimization depends on calibration quality and did not beat the simpler fixed policy here.

## 22. Training-derived lookup dictionary

- Chronology: September 27.
- Question: Could aliases derived only from labeled training data resolve difficult names and addresses?
- Code and artifacts: `experiments/codex7_train_lookup_dictionary_01/`.
- Strategy: name, address, transliteration, and rare-token lookup features built without external data or POLICY_DEV truth.
- Data: model train and POLICY_DEV.
- Verified result: Macro F0.5 0.9521339038405161, delta -0.0016575032391447087 versus control.
- Disposition: REJECTED.
- Lesson: label-derived dictionaries were brittle and added leakage-review cost without improving qualification.

## 23. Exact 59-feature model reproduction and selected test production

- Chronology: September 27, approximately 20:27 to 21:26 IST.
- Question: Could the selected cross-script model be reconstructed and used on the frozen full test graph without changing final decisions?
- Code and artifacts: `experiments/asmi_crossscript_reproduction_01/`, `output/asmi-crossscript-59-reproduced-v1/`, and the seven frozen source modules now under `src/concord/legacy_amazon/`.
- Strategy: deterministic LightGBM refit, exact schema validation, one complete test scoring pass, global ownership, and 0.64 thresholds.
- Data: 3,376,945 training candidate rows, frozen POLICY_DEV, and 87,934,151 test pairs.
- Verified result: exact POLICY_DEV emitted links and metric, selected output hash `0153c2ad53f0cfbecce5339075968588d131d3144f6c85c49bb2a5a05741d145`, public Macro F0.5 0.955136.
- Model hashes: text `7c1797a78d4585647c818868a1d8960790cd2a5f77b9c90a36af9a2a4c710784`; joblib `c5b0e2246794f5e79d6cfed1e16d82040d682bdee4cf94eccb760d61e69d6610`.
- Disposition: PROMOTED. This is the `amazon-ml-2026-final` baseline.
- Lesson: exact decision equivalence and artifact validation were more important than negligible floating-point probability differences.

## 24. Later external and meta-decoder experiments

- Chronology: September 27 after the selected submission, approximately 22:00 onward.
- Question: Could external evidence, new candidate discovery, or a final meta-decoder improve difficult cases?
- Code and artifacts: `experiments/e1_external_evidence_verifier_01/`, `fast_external_candidate_rescue_01/`, `external_web_identity_decoder_01/`, `final_last_chance_meta_decoder/`, `e1_external_production/`, `e3_base_policy_replay_20260927_2333/`, and `e3_tsv_patch/`.
- Strategy: public-web evidence, truth-blind candidate proposals, experimental overrides, and meta decisions.
- Data: training and POLICY_DEV only for evaluated branches; selected test output was not modified.
- Verified results: candidate rescue found 61 proposals with 1 true rescue and 60 false rescues; the frozen rule added zero POLICY_DEV edges and gained 0.0. The web decoder changed no decisions and gained 0.0. The final meta-decoder changed two empty decisions and lost 0.00010182262498736883.
- Disposition: LATER EXPERIMENT. Not part of the 0.955136 submission.
- Lesson: external evidence added provenance and competition-policy risk without a verified metric gain. The zero-delta replay remained byte-identical and was not uploaded.

## Archive policy

The original experiment directories remain on disk for now. `archive_manifest/experiment_artifacts.json` records their sizes and preservation status. No large generated experiment artifact is copied into Git. Future cleanup must wait until the GitHub repository, tag, documentation, and manifests have been pushed and independently verified.
