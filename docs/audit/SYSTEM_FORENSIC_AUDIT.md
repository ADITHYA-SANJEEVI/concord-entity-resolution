# System Forensic Audit: Concord Preserved Baseline

**Repository:** `concord-entity-resolution`  
**Preserved Baseline Commit:** `1133bfda496e2be59623fe154ec3dac45c13361f`  
**Preserved Baseline Tag:** `amazon-ml-2026-final`  
**Branch:** `main` (clean working tree, identical to origin)  
**Audit Scope:** Repository forensics, code inspection, and baseline verification prior to architecture freeze. No production source modification or external re-execution.

---

## 1. Executive Summary & Verdict

Concord began as Team Aurorawave's solution to the Amazon ML Challenge 2026 Business Entity Resolution task (Adithya Sanjeevi, Asmi Balla, Shreya Saha). The preserved baseline at commit `1133bfd` contains approximately 2,100 lines of verified production Python, authoritative schemas, serializations, cryptographic manifests, and a 24-experiment ledger.

The system addresses large-scale multilingual entity resolution:
> **Scale Summary:** Resolving 1,732,544 Source-1 (S1) query business entities against a target universe of approximately 9,969,589 valid Source-2 (S2) and Source-3 (S3) target records. Through bounded multi-view sparse retrieval, the pipeline reduced an enormous potential Cartesian comparison space into a bounded candidate graph of 87,934,151 pairs, scored each candidate with a 59-feature LightGBM model, enforced deterministic global target ownership, and applied a fixed threshold of 0.64.

**Verdict:** The repository is an exceptionally well-preserved competition artifact. Cryptographic hashes tie source code, schemas, and configurations directly to the submitted output files (`matching_results.tsv` and `candidate_pairs.tsv`). It is structurally clean, methodologically documented, and an ideal foundation for Concord's flagship architecture.

---

## 2. Material Inspected

Every file across the repository (42 files total) was inspected during the forensic pass:

| Directory / File Group | File Count | Lines of Code / Docs | Description & Status |
|---|---|---|---|
| `README.md` | 1 | 93 | Top-level project summary, baseline metrics, and reproduction profile. |
| `pyproject.toml` | 1 | 36 | Build system (`hatchling`), dependencies, optional dependency groups (`amazon`, `dev`). |
| `configs/amazon_ml_2026.yaml` | 1 | 23 | Descriptive config reflecting the final competition architecture. |
| `docs/*.md` | 10 | ~570 | Formal documentation (origin, architecture, experiment ledger, failure analysis, provenance, reproducibility, results, resume evidence, roadmap, pipeline). |
| `src/concord/legacy_amazon/*.py` | 7 | ~1,980 | Production source code: graph builder, scorer, test production runner, cross-script generator, pipeline runner, submission validator, output comparator. |
| `src/concord/legacy_amazon/artifacts/` | 3 | ~30 | Authoritative schema (`ordered_59_feature_schema.json`), LightGBM parameters (`lightgbm_config.json`), and artifact README. |
| `archive_manifest/*.json` | 4 | ~320 | Machine-readable manifests: `artifacts.json`, `experiment_artifacts.json`, `final_submission.json`, `source_snapshot.json`. |
| `src/concord/provenance.py` | 1 | 21 | Pinned SHA-256 identities of final outputs and streaming hash utility. |
| `tests/*.py` | 2 | 56 | Contract and manifest regression tests (`test_manifests.py`, `test_preserved_contract.py`). |
| `examples/synthetic/*.tsv` | 3 | 9 | Non-confidential synthetic data fixtures (`source1.tsv`, `source2.tsv`, `source3.tsv`) documenting input shape. |
| `src/concord/{modules}/__init__.py` | 8 | ~25 | Package namespace stubs reserved for new Concord architecture (`retrieval`, `features`, `modeling`, `inference`, `evaluation`, `utils`). |

---

## 3. Repository Inventory & Artifact Classification

Each artifact in the preserved repository is classified into one of the following archival categories:

1. **PRESERVE VERBATIM (Historical Baseline & Reference):**
   - `src/concord/legacy_amazon/frozen_full_graph_builder.py` (Five-view sparse retrieval and graph union)
   - `src/concord/legacy_amazon/frozen_stage1_55_scorer.py` (55-feature generation, OOF training, threshold calibration)
   - `src/concord/legacy_amazon/frozen_test_production.py` (Full test production orchestrator for Modal)
   - `src/concord/legacy_amazon/qualified_crossscript_generator.py` (Deterministic 4-feature transliteration/cross-script generator)
   - `src/concord/legacy_amazon/run_pipeline.py` (Portable pipeline entry point)
   - `src/concord/legacy_amazon/artifacts/ordered_59_feature_schema.json` (Authoritative 59-feature order and definitions)
   - `src/concord/legacy_amazon/artifacts/lightgbm_config.json` (Authoritative hyperparameters)
   - `archive_manifest/*.json` (Cryptographic records of omitted files, sources, and experiments)
   - `docs/*.md` (Historical records and narrative lineage)

2. **REUSABLE UTILITIES & CONTRACTS:**
   - `src/concord/legacy_amazon/validate_submission.py` (Memory-efficient submission formatting and constraint validator)
   - `src/concord/legacy_amazon/compare_outputs.py` (Streaming semantic and byte-level TSV comparison tool)
   - `src/concord/provenance.py` (Pinned hash constants and chunked file hashing)
   - `tests/test_manifests.py` & `tests/test_preserved_contract.py` (Baseline regression assertions)
   - `examples/synthetic/` (Non-sensitive TSV schemas and test records)
   - `pyproject.toml` (Base project packaging)

3. **SCAFFOLDING (Clean Namespace Stubs):**
   - `src/concord/__init__.py`
   - `src/concord/retrieval/__init__.py`
   - `src/concord/features/__init__.py`
   - `src/concord/modeling/__init__.py`
   - `src/concord/inference/__init__.py`
   - `src/concord/evaluation/__init__.py`
   - `src/concord/utils/__init__.py`
   *(All represent future package boundaries; none contain production logic.)*

4. **INTENTIONALLY OMITTED / RESTRICTED:**
   - Organizer datasets (`train_source*.tsv`, `test_source*.tsv`, `train_ground_truth.tsv` — ~2.52 GB total): Private challenge data excluded due to lack of redistribution rights.
   - Trained model weights (`cross_script_59_reproduced_model.joblib` [1.9 MB] and `.txt` [4.2 MB]): Excluded due to model rights derived from private data. Hashes preserved.
   - Intermediate caches and matrices (~24.6 GB across 28 experiment directories): Preserved on external storage; documented in `archive_manifest/`.
   - Preserved output files (`matching_results.tsv` [96 MB], `candidate_pairs.tsv` [1.16 GB], `Aurorawave_submission.zip` [523 MB]): Hashes pinned in `provenance.py`.

---

## 4. Verified Historical Pipeline Summary

The preserved V3 baseline (`amazon-ml-2026-final`) executes in five distinct stages:

1. **Normalization:**
   - Text fields (`business_name`, `business_address`) undergo Unicode NFKD decomposition, combining-character removal, and case folding via `fold()`. No stopword removal, abbreviation expansion, or entity suffix stripping.

2. **Multi-View Bounded Sparse Retrieval:**
   - Data is partitioned by country. Joint query-target TF-IDF vectorizers (`min_df=2`, `max_df=0.05`, `sublinear_tf=True`, float32) are fit on an unseeded/seeded 3M sample.
   - Five views are retrieved using `sparse_dot_topn.sp_matmul_topn`:
     - `name`: char_wb trigrams (top-5)
     - `compact`: char trigrams with whitespace removed (top-5)
     - `address`: word unigrams (top-5)
     - `combined`: 50/50 weighted combination of name and address (top-10)
     - `reverse`: combined view transposed (targets query sources, top-8)
   - Bounded results are merged via DuckDB full outer join, generating `retrieval_view_mask` (bitmask 1..31).

3. **Feature Engineering (59 Features):**
   - **55 Base Features:** 29 direct string, token, and numeric metrics; 4 exact cosine similarities; 5 retrieval ranks; 17 DuckDB windowed graph-context features (query-source ranks, delta-to-best scores, target-owner ranks, target delta-to-best, and rival margins).
   - **4 Cross-Script Features:** Generated via Unidecode transliteration: transliterated name char-trigram Jaccard (`f55`), maximum RapidFuzz ratio across original/transliterated variations (`f56`), script-mismatch indicator (`f57`), and transliterated address token Jaccard (`f58`).

4. **LightGBM Scoring:**
   - 600 estimators, learning rate 0.05, 63 leaves, min child samples 100, L2 regularization 1.0, float32 feature inputs. Emits pairwise probabilities `predict_proba(X)[:, 1]`.

5. **Decision Policy & Global Ownership:**
   - Targets (S2/S3) are strictly assigned to at most one S1 owner via `ROW_NUMBER() OVER(PARTITION BY target_id ORDER BY score DESC, s1_id ASC)`.
   - Thresholding: S1-target pairs with score $\ge 0.640$ are accepted.
   - Output TSVs are written in deterministic order; empty S1 rows are preserved to indicate zero matches.

---

## 5. Major Strengths of the Preserved Baseline

1. **Massive Candidate-Space Reduction:** Reduced an astronomical Cartesian search space down to 87,934,151 high-quality pairs without all-pairs comparison, maintaining a retrieval recall ceiling of $>0.999$ on validation samples.
2. **Reverse Retrieval Innovation:** The reverse retrieval lane (targets querying sources) captured asymmetric name/address variations that forward retrieval missed (e.g., 121 unique truth links recovered on validation).
3. **Graph-Context Feature Engineering:** Rather than scoring pairs in isolation, the 17 graph-context features capture competitive pressure (rival margins, delta to top candidate), which proved essential for LightGBM to arbitrate ownership.
4. **Target Ownership Enforcement:** A simple, deterministic SQL window resolution prevented duplicate target assignments globally, ensuring zero target contention.
5. **Rigorous Preservation Discipline:** Output file hashes, model digests, schema fingerprints, and negative experiment outcomes were carefully recorded and pinned.

---

## 6. Major Architectural Gaps & Vulnerabilities

1. **Linux/Multiprocessing Fork Dependency:** Feature generation in `frozen_stage1_55_scorer.py` relies on Python's `get_context("fork")`, making the historical code unrunnable natively on Windows without WSL2.
2. **Hardcoded Environments:** Source code contains fixed path literals (`/volume`, `/tmp/duckdb_*`, `C:\Users\adith\...`).
3. **Distribution Shift (France at Test Time):** The model was trained and calibrated strictly on US and India data. France was introduced exclusively in the test set. Threshold calibration was never verified on French entity distribution.
4. **Transliteration Bounded to Features:** Transliteration was applied only during feature scoring, not during retrieval blocking. If a cross-script candidate failed TF-IDF retrieval, transliteration features could not rescue it.
5. **Global Ownership Cross-Split Dependency:** Because target ownership depends on all competing S1 queries, evaluating an arbitrary subset in isolation can yield different ownership decisions than evaluating the full population.
6. **No Distributable Public Benchmark:** The repository lacks a standalone, distributable benchmark with labels to verify end-to-end training and inference without private Amazon files.

---

## 7. Red-Team Findings

1. **Finding RT-1 (Scale Interpretation):** Early summaries incorrectly phrased the scale as a multiplication ($1.73\text{M} \times 9.97\text{M} = 87.9\text{M}$). In reality, $1.73\text{M} \times 9.97\text{M} \approx 17.2\text{ trillion}$ candidate comparisons; the 87.9M graph represents an extreme sparse reduction ($<0.0006\%$ of Cartesian space).
2. **Finding RT-2 (Seed Recovery Uncertainty):** The LightGBM configuration explicitly records `seed_recovery: "DEFAULTED_TO_42_NO_PRIOR_VALUE_FOUND"`. While the deterministic refit achieved probability parity within $1.97 \times 10^{-11}$, the exact original training seed was unrecovered.
3. **Finding RT-3 (Target Leakage Risk in Custom Splits):** In entity resolution where targets can link to training queries, naive random splitting can leak target entity representations across folds.
4. **Finding RT-4 (OOD Degradation Risk):** Zero-shot country generalization (France) without localized address tokenization or country-specific abbreviation expansion is fragile.
5. **Finding RT-5 (Decoupled Stage Failures):** The historical system lacked structured error attribution. A missed match could be caused by retrieval, ranking, ownership, or decoding, but no automated subsystem logged where the link dropped out.

---

## 8. Conclusion

The repository is technically sound, highly disciplined, and verified against all preserved contract tests. Concord will not discard or rewrite this baseline. Instead, Concord will preserve `legacy_amazon` intact as a benchmark reference and construct clean, typed, cross-platform modules outside `legacy_amazon` to deliver production-grade entity resolution.
