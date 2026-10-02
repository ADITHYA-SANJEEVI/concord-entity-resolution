# Proposed Experiment and Benchmark Contract v1.1

**Status:** AUTHORITATIVE TARGET CONTRACT FOR NEW CONCORD

---

## 1. Instance schema

A run manifest uses:

```json
{
  "schema_version": "concord.experiment.v1",
  "experiment_id": "exp-...",
  "timestamp_utc": "2026-10-02T00:00:00Z",
  "git": {
    "commit_sha": "...",
    "dirty": false
  },
  "provenance": {
    "dataset_fingerprint": "...",
    "split_fingerprint": null,
    "dataset_track": "SYNTHETIC_PUBLIC"
  },
  "configuration_fingerprint": "...",
  "pipeline_configuration": {},
  "metrics": {},
  "operational": {},
  "artifacts": {},
  "evidence": {
    "class": "D",
    "notes": []
  },
  "disposition": "COMPLETED"
}
```

This is an **instance example**, not a JSON Schema.

A separate JSON Schema file may declare Draft 2020-12.

No invented measurements are permitted in templates.

---

## 2. Experiment statuses

Allowed:

- `PLANNED`
- `RUNNING`
- `COMPLETED`
- `FAILED`
- `INVALIDATED`

Promotion is a separate disposition:

- `PROMOTED`
- `REJECTED`
- `DIAGNOSTIC_ONLY`
- `INCONCLUSIVE`

A failed run is never silently removed.

---

## 3. Evidence classes

Reuse the project evidence ledger:

- A — directly verified preserved evidence;
- B — strongly supported historical evidence;
- C — historical context / unrecovered;
- D — newly reproduced controlled run;
- E — aspirational/planned.

A new benchmark result is class D only when the run artifacts and manifest exist.

---

## 4. Retrieval benchmark contract

For each retrieval run record:

### Quality
- truth-pair recall / Pair Completeness;
- Recall@1;
- Recall@5;
- Recall@10;
- Recall@20;
- zero-candidate S1 count/rate.

### Cost
- candidate pairs;
- mean/p50/p90/p99/max candidates per S1;
- Reduction Ratio against eligible Cartesian universe;
- candidates per recovered truth;
- wall-clock runtime;
- CPU time if available;
- peak RSS;
- bytes read/written if measurable.

### Provenance science
- unique truths rescued by each lane;
- pairwise lane overlap;
- truths found by exactly N lanes;
- candidate cost by lane;
- marginal truth recall per added million candidates.

No metric is reported without the population/split/variant.

---

## 5. Retrieval frontier

For configs differing in K, lanes, or challenger logic:

- plot truth recall vs candidate pairs;
- plot truth recall vs runtime;
- plot truth recall vs peak RSS;
- mark Pareto-nondominated configs.

Promotion requires:
- pre-registered primary population;
- no regression on hard safety invariants;
- either Pareto dominance or a declared utility trade-off.

---

## 6. Scoring benchmark contract

Report:

- AUROC;
- AUPRC;
- log loss;
- Brier score;
- calibration curve/ECE where sample size supports it;
- ranking metrics where a valid per-query ranking target exists;
- score distributions for positives/negatives;
- cohort breakdowns.

Do not treat AUROC as end-to-end ER quality.

---

## 7. Ownership / decoder metrics

Report:

- target contention count;
- ownership-loss truth count;
- rival-margin distribution;
- macro F0.5;
- macro precision;
- macro recall;
- exact-set accuracy;
- zero-match accuracy/F0.5 cohort;
- multi-match cohort metrics;
- accepted-link count.

---

## 8. Cohort dimensions

Where supported by labels:

- SAME_SCRIPT;
- CROSS_SCRIPT;
- country label;
- COUNTRY_OOD;
- UNSEEN_ENTITY;
- CORNER_CASE;
- ZERO_MATCH;
- SINGLE_MATCH;
- MULTI_MATCH;
- SINGLE_LANE;
- HIGH_AMBIGUITY.

Every cohort result includes sample size.

---

## 9. Public benchmark tracks

### P0 Synthetic
Committed. Required on every CI run.

### P1 WDC Products
Preferred public quality benchmark.

Record:
- exact hardness/corner-case variant;
- unseen-entity setting;
- development-set size;
- pairwise vs multi-class formulation.

Never merge variants into an unlabeled average.

### P2 WDC large-scale product corpus
Optional scale track.

Record whether:
- full corpus;
- sampled subset;
- gold-standard-only;
- retrieval-only.

---

## 10. External comparator policy

Allowed comparators:

- exact/rule baseline;
- Splink;
- Ditto or another neural matcher;
- other well-defined public baselines.

Rules:

- same public split/variant;
- same candidate boundary where meaningful;
- exact versions/configs;
- no literature number copied into a Concord results table as if locally reproduced.

---

## 11. Cross-script challenger protocol

Historical baseline:
- transliteration features only;
- no transliteration retrieval lane.

Challenger:
- add one or more transliterated retrieval views;
- preserve fixed historical five-view baseline untouched;
- report candidate-cost overhead;
- report cross-script truth recall delta;
- report overall recall delta;
- report downstream F0.5 only after C3 exists.

Promotion:
- controlled, pre-registered;
- null/negative result preserved;
- no "improvement" claim without class-D evidence.

---

## 12. Adaptive candidate-budget challenger

Optional C4 experiment.

Inputs must be pre-scoring, such as:
- missingness;
- token lengths;
- script metadata;
- top retrieval similarity concentration;
- lane agreement.

Outputs:
- bounded per-query K/budget;
- hard global max K.

Benchmark against fixed-K baseline on:
- truth recall;
- candidates;
- runtime;
- memory.

No promotion without a Pareto or pre-declared utility win.

---

## 13. Stability-vs-confidence protocol

Primary unit: S1 resolution set.

Ground-truth target:

`error_i = 1` iff predicted set != true set.

### Confidence baselines

At minimum:
- top candidate score;
- minimum accepted score for non-empty sets;
- best rejected score;
- score gap where defined.

Zero-match confidence must be explicitly defined and separately validated.

### Stability features

Raw only:
- accepted-target lane counts;
- alternate-lane availability;
- ownership margins;
- threshold margins;
- candidate ambiguity ratio;
- candidate-set size/density.

A cheap lane-drop analysis is called **candidate-availability under lane removal**.

It must not be described as "the final resolution survives lane removal" unless rescoring/ownership/decoding are actually rerun.

### Statistics

Report:
- AUROC;
- AUPRC on error class;
- risk-coverage curve;
- risk at 90% and 95% coverage;
- paired bootstrap confidence interval for deltas.

Interpretation:
- CI supporting improvement -> evidence of improvement;
- CI supporting degradation -> evidence of degradation;
- otherwise -> no clear evidence of difference.

`p > 0.05` alone is not equivalence.

---

## 14. Drift lens

For two datasets/cohorts compare:

- missingness;
- scripts;
- field lengths/tokens;
- candidate density;
- lane usage;
- score distributions;
- calibration;
- failure-stage mixture.

Use statistical distances only when their assumptions and sample sizes are documented.

---

## 15. Benchmark profiles

### `smoke`
- tiny synthetic;
- deterministic;
- seconds;
- CI-friendly.

### `public`
- WDC Products or other declared public benchmark;
- full quality report;
- exact dataset version/variant.

### `scale`
- larger retrieval/resource profile;
- exact hardware;
- exact sample/full-corpus scope;
- runtime/memory/disk metrics.

---

## 16. Reproducibility

A promoted experiment must record:

- git commit;
- dirty flag;
- Python version;
- OS;
- CPU;
- available RAM;
- dataset fingerprint;
- split fingerprint;
- config fingerprint;
- normalization version;
- retrieval config hash;
- feature schema hash;
- model hash;
- decoder hash;
- random seeds;
- output artifact hashes.

A repeated synthetic run should produce identical logical output hashes unless the experiment explicitly permits nondeterminism.
