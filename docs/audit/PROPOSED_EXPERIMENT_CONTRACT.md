# Proposed Experiment Contract & Stability Protocol

**Repository:** `concord-entity-resolution`  
**Status:** SUPERSEDED PROPOSAL. New experiments use the authoritative
[v1.1 experiment contract](../../Concord_Architecture_v1_1_AstraStyle/docs/audit/PROPOSED_EXPERIMENT_AND_BENCHMARK_CONTRACT_V1_1.md).
The example below is an older illustrative template, not an executed run or measured
result. Its legacy schema identifier is retained as a reference to the frozen artifact.

---

## 1. Canonical Experiment Manifest Schema

Every Concord experiment—whether a retrieval ablation, a new feature set, a threshold change, or a stability evaluation—must output a canonical UTF-8 JSON manifest adhering to this contract. Experiments lacking this manifest cannot be promoted to the project registry.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "experiment_id": "exp-20261015-multiview-retrieval-v2",
  "timestamp": "2026-10-15T18:24:00Z",
  "author": "Adithya Sanjeevi",
  "git": {
    "commit_sha": "1133bfda496e2be59623fe154ec3dac45c13361f",
    "branch": "main",
    "dirty": false
  },
  "provenance": {
    "dataset_fingerprint": "a3f5b9...",
    "split_fingerprint": "b7c2d1...",
    "dataset_track": "SYNTHETIC_PUBLIC"
  },
  "pipeline_configuration": {
    "normalization": {
      "version": "nfkd-casefold-v1",
      "strip_accents": true,
      "casefold": true
    },
    "retrieval": {
      "strategy": "five_view_sparse_tfidf",
      "views": ["name", "compact", "address", "combined", "reverse"],
      "k_per_view": {
        "name": 5,
        "compact": 5,
        "address": 5,
        "combined": 10,
        "reverse": 8
      },
      "max_fit_sample": 3000000,
      "random_seed": 0
    },
    "features": {
      "schema_version": "asmi-crossscript-reproduced-59-v1",
      "schema_sha256": "ed766a44c8c5bb20abc8d6473ba95cffd9755bd4a65c88752b34adab0705c5f0",
      "feature_count": 59,
      "dtype": "float32"
    },
    "negative_sampling": {
      "strategy": "retrieval_derived_implicit_hard_negatives",
      "ratio": "all_unmatched_candidates"
    },
    "modeling": {
      "model_type": "LGBMClassifier",
      "hyperparameters": {
        "n_estimators": 600,
        "learning_rate": 0.05,
        "num_leaves": 63,
        "min_child_samples": 100,
        "reg_lambda": 1.0,
        "subsample": 1.0,
        "colsample_bytree": 1.0,
        "random_state": 42
      },
      "model_artifact_sha256": "c5b0e2246794f5e79d6cfed1e16d82040d682bdee4cf94eccb760d61e69d6610"
    },
    "decoding": {
      "policy": "global_target_ownership",
      "ownership_tie_break": "s1_id_ascending",
      "threshold_s2": 0.640,
      "threshold_s3": 0.640
    }
  },
  "metrics": {
    "retrieval": {
      "recall_at_1": 0.8421,
      "recall_at_5": 0.9412,
      "recall_at_10": 0.9785,
      "recall_at_20": 0.9931,
      "mean_candidate_density": 50.7,
      "zero_candidate_rate": 0.0012
    },
    "resolution": {
      "macro_f05": 0.959364,
      "macro_precision": 0.9712,
      "macro_recall": 0.9154,
      "tp_links": 9826,
      "fp_links": 162,
      "fn_links": 757,
      "zero_match_s1_count": 100939
    },
    "cohort_metrics": {
      "SAME_SCRIPT": { "macro_f05": 0.9721, "sample_size": 12000 },
      "CROSS_SCRIPT": { "macro_f05": 0.9184, "sample_size": 3113 },
      "COUNTRY_US": { "macro_f05": 0.9754, "sample_size": 9500 },
      "COUNTRY_INDIA": { "macro_f05": 0.9321, "sample_size": 5613 },
      "COUNTRY_FRANCE": { "macro_f05": null, "notes": "Unlabeled in train" }
    }
  },
  "operational": {
    "total_runtime_seconds": 8942.5,
    "peak_memory_mib": 2845.2,
    "platform": {
      "os": "Windows 11 / Linux 6.8",
      "cpu_threads": 16,
      "python_version": "3.12.10"
    }
  },
  "evidence_classification": "B",
  "disposition": "PROMOTED",
  "notes": "Verified against frozen baseline contracts."
}
```

---

## 2. Protocol: S1-Level Stability vs. Confidence Experiment

### 2.1 Research Hypothesis
> **Hypothesis:** Multi-stage entity resolution fragility (measured by retrieval lane redundancy, single-lane survival, ownership rival margin, and threshold proximity) predicts set-level resolution errors significantly better than the model's raw top-pair probability alone.

### 2.2 Primary Experimental Unit
The primary experimental unit is the **Source-1 Query Entity Resolution Set**, matching the macro-F0.5 objective. Pair-level evaluations serve as secondary diagnostics only.

For each S1 entity $i$:
- Let $\hat{T}_i$ be the set of predicted target IDs emitted by the pipeline.
- Let $T_i^*$ be the true set of target IDs from ground truth.
- Define binary set-level resolution success:
  $$Y_i = \mathbb{I}\left(\hat{T}_i = T_i^*\right)$$
  *(Alternatively, evaluate $Y_i = \mathbb{I}\left(\text{F0.5}_i \ge 0.999\right)$ for exact correctness).*
- An error occurs when $Y_i = 0$ (either a false positive, false negative, or target substitution).

### 2.3 Baseline vs. Stability Predictors

1. **Baseline Predictor ($S_{\text{conf}}$):**
   $$S_{\text{conf}}(i) = \begin{cases} \max_{t \in \hat{T}_i} \hat{P}(i, t) & \text{if } |\hat{T}_i| > 0 \\ 1.0 - \max_{t \in \text{Cands}(i)} \hat{P}(i, t) & \text{if } |\hat{T}_i| = 0 \end{cases}$$
   The classifier's raw probability margin.

2. **System Stability Features ($S_{\text{stab}}$):**
   - **Lane Redundancy:** Minimum number of retrieval views supporting any accepted target in $\hat{T}_i$.
   - **Single-Lane Survival:** Binary indicator whether $\hat{T}_i$ remains unchanged if any single retrieval lane is removed ($K$-lane counterfactual).
   - **Rival Ownership Margin:** Minimum margin $\min_{t \in \hat{T}_i} \left(\text{score}(i, t) - \text{runner\_up}(t)\right)$ across accepted targets.
   - **Threshold Proximity:** $\min_{t \in \hat{T}_i} \left(\text{score}(i, t) - 0.640\right)$.
   - **Candidate Ambiguity Ratio:** Ratio of 2nd highest candidate score to 1st highest candidate score in $\text{Cands}(i)$.

### 2.4 Statistical Evaluation & Metrics
To avoid circular reasoning, stability features are evaluated on held-out evaluation splits (e.g., `POLICY_DEV` or synthetic validation partitions) using:
1. **AUROC:** Ability of $S_{\text{conf}}$ vs. $S_{\text{stab}}$ (or a logistic composite) to discriminate $Y_i = 1$ vs. $Y_i = 0$.
2. **AUPRC (Precision-Recall AUC):** Evaluated specifically on the minority error class ($Y_i = 0$).
3. **Risk-Coverage Curves:** Plot error rate against the fraction of S1 queries retained when queries with low stability/confidence are routed to human review or abstention.
4. **Selective Accuracy:** Error rate at fixed coverage thresholds of **90%** and **95%**.

### 2.5 Null Result & Pre-Registration Policy
- **Scientific Integrity:** The outcome of this study is **NOT** predicted or assumed in advance.
- If $S_{\text{stab}}$ does not provide a statistically significant improvement over $S_{\text{conf}}$ (paired bootstrap $p > 0.05$), the result is recorded as a **confirmed null finding**.
- A null finding is scientifically valuable: it demonstrates that the 59-feature LightGBM model already successfully incorporates competitive graph context, rendering post-hoc stability metrics redundant.
