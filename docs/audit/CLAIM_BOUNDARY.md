# Claim Boundary: Verifiable vs. Unsafe Statements

**Repository:** `concord-entity-resolution`  
**Purpose:** Establish strict, interview-defensible claim boundaries for Concord. Every public statement, portfolio description, or resume bullet must fall into one of the designated categories below.

---

## 1. Boundary Taxonomy

- **Category 1: SAFE NOW** — Directly supported by code, authoritative schema, or cryptographic manifests in the repository.
- **Category 2: SAFE AS HISTORICAL / PRESERVED** — Supported by preserved competition artifacts, official validator runs, or qualification reports; must be phrased as historical/competition evidence.
- **Category 3: SAFE AFTER PRIVATE REPRODUCTION** — Defensible only after private re-execution on authorized data (e.g., full test set graph generation).
- **Category 4: SAFE AFTER NEW EXPERIMENT** — Novel Concord architectural metrics requiring new experimental execution (e.g., Gate C4 stability results).
- **Category 5: UNSAFE / DO NOT CLAIM** — Contradicted by repository evidence, unverified prompt recollections, or unsupported marketing claims.

---

## 2. Definitive Claim Classification Matrix

| Claim / Metric | Permitted Resume / Interview Phrasing | Status Category | Required Context & Boundary Conditions |
|---|---|---|---|
| **Challenge Origin** | "Engineered a business entity-resolution system for the Amazon ML Challenge 2026 as part of Team Aurorawave." | **SAFE NOW** | Accurately describes team and task origin. |
| **59-Feature Schema** | "Designed and deployed a fixed 59-feature schema combining direct string metrics, exact TF-IDF cosines, retrieval ranks, and DuckDB graph-context features." | **SAFE NOW** | Schema and code are preserved and tested in Git. |
| **Multi-View Bounded Retrieval** | "Architected a five-view sparse TF-IDF retrieval system (name, compact name, address, combined, reverse) bounded by `sparse_dot_topn`." | **SAFE NOW** | Direct code implementation in `frozen_full_graph_builder.py`. |
| **Global Target Ownership** | "Enforced deterministic global target ownership where each target is resolved to at most one source query via score-partitioned window queries." | **SAFE NOW** | Implemented directly in SQL / DuckDB pipeline logic. |
| **Deterministic Tie-Breaking & Validation** | "Built deterministic sorting, thresholding (0.640), and structural validation ensuring submission integrity and subset compliance." | **SAFE NOW** | Provenance hashes and validator scripts verified. |
| **Public Leaderboard Score** | "Achieved a verified public leaderboard Macro F0.5 of 0.955136." | **SAFE AS HISTORICAL** | Preserved historical submission evidence. Do not imply current live portal verification. |
| **Public Leaderboard Rank** | "Placed rank 2502 on the public competition leaderboard." | **SAFE AS HISTORICAL** | Preserved portal evidence. |
| **POLICY_DEV Metric** | "Recorded a Macro F0.5 of 0.959364 on the frozen POLICY_DEV validation split." | **SAFE AS HISTORICAL** | Preserved in `final_submission.json` and qualification records. |
| **Entity Population Scale** | "Resolved 1,732,544 source entities against an index of approximately 9,969,589 target entities." | **SAFE AS HISTORICAL** | Supported by test production constants and validator manifests. |
| **Candidate Graph Reduction** | "Reduced an enormous Cartesian comparison space down to an 87,934,151-pair candidate graph using bounded multi-view retrieval." | **SAFE AS HISTORICAL** | **Mandatory correction:** Never phrase as $1.73\text{M} \times 9.97\text{M} = 87.9\text{M}$. Emphasize sparse candidate reduction. |
| **Accepted Match Volume** | "Emitted 5,708,382 accepted matches and 100,939 verified zero-match records." | **SAFE AS HISTORICAL** | Supported by output manifests and validator checks. |
| **Cross-Script Development Gain** | "Historical development ledger records a +0.00558 Macro F0.5 gain on POLICY_DEV from adding 4 deterministic transliteration features." | **SAFE AS HISTORICAL** | Must be cited as historical experiment-ledger evidence (#13), NOT newly reproduced. |
| **Full 87.9M Clean-Room Rerun** | "Re-executed the entire 87.9M-pair pipeline from scratch in a local environment." | **SAFE AFTER REPRODUCTION** | Do not claim full local re-execution until a high-memory Linux run with private data is completed. |
| **Model Retrain Parity** | "Achieved deterministic model retraining parity within $1.97 \times 10^{-11}$ max probability error." | **SAFE AFTER REPRODUCTION** | Requires private model weights and training split to rerun. |
| **End-to-End Latency / Throughput** | "Achieved X pairs per second throughput or Y ms per query latency." | **SAFE AFTER NEW EXPERIMENT** | No granular latency or query-time profiling survives in the repository. |
| **Recall@K Curves (1, 5, 10, 20)** | "Multi-view retrieval achieved Recall@1/5/10/20 of X%." | **SAFE AFTER NEW EXPERIMENT** | Planned for Gate C2 evaluation on clean datasets. |
| **System Stability vs. Error Prediction** | "System resolution fragility predicts entity errors better than raw model confidence." | **SAFE AFTER NEW EXPERIMENT** | Planned for Gate C4 study. Must report exact results, including null findings. |
| **Later Pipeline Result (~0.966)** | "Achieved ~0.966 Macro F0.5 in post-submission experiments." | **UNSAFE / DO NOT CLAIM** | **Unrecovered team recollection.** No code, log, or output hash exists in the repository for this figure. |
| **Peak RAM ~2.9 GiB** | "Pipeline executed with a peak RAM of ~2.9 GiB." | **UNSAFE / DO NOT CLAIM** | **Unverified prompt context.** No committed artifact or run log supports this memory number. |
| **Candidate Volumes ~32.05M / ~16.76M** | "Candidate generation produced 32.05M raw candidates pruned to 16.76M at K=20." | **UNSAFE / DO NOT CLAIM** | **Unverified prompt context.** Does not match any committed manifest. |
| **Arbitrary Subset Recall Ceilings** | "Strict prefix ceiling: 0.976654; retrieval ceiling: 0.993058." | **UNSAFE / DO NOT CLAIM** | **Unverified prompt context.** The only preserved sample oracle is 0.999623 on a 5k sample (Ledger #7). |
| **Top 50 / Top 100 / PPI Recognition** | "Selected for PPI / Top 50 finish." | **UNSAFE / DO NOT CLAIM** | No evidence exists in the repository. Rank 2502 is the only verified standing. |
| **World-First / Novel Architecture** | "First proof-carrying entity-resolution architecture in literature." | **UNSAFE / DO NOT CLAIM** | No comparative literature review exists. Describe the concrete engineering without novelty hype. |
| **Live Distributed System** | "Concord operates as a fault-tolerant distributed consensus engine." | **UNSAFE / DO NOT CLAIM** | **Confuses Concord with Relay.** Concord is a bounded IR/ER ML pipeline, not a distributed system. |

---

## 3. Safe Resume Bullets (Approved Verbatim)

```text
- Built a large-scale business entity-resolution pipeline for the Amazon ML Challenge 2026 (Team Aurorawave), achieving a verified 0.955136 public Macro F0.5 (Rank 2502).
- Reduced a massive potential Cartesian search space across 1.73M source records and 9.97M target entities into a bounded 87.9M-pair candidate graph using five-view sparse TF-IDF retrieval (name, compact name, address, combined, reverse).
- Engineered a 59-feature schema encompassing string metrics, exact TF-IDF cosines, retrieval ranks, DuckDB windowed graph-context features, and deterministic Unidecode cross-script signals.
- Trained a 59-feature LightGBM classifier and enforced global target ownership via score-partitioned window queries, producing 5.7M accepted links with deterministic subset validation.
- Preserved complete experiment lineage across 24 historical iterations with cryptographic manifests, schema contracts, and negative-result documentation.
```
