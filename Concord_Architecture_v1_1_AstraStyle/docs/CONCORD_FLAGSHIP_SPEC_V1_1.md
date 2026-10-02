# Concord Flagship Specification v1.1

**Authority:** Consolidated implementation specification after Architecture Amendment 001  
**Baseline freeze commit:** `3aa3211`  
**Legacy baseline:** `1133bfd` / `amazon-ml-2026-final`

---

## Thesis

Concord is an evidence-centric multilingual entity-resolution system for reducing massive candidate universes into bounded, explainable, reproducible identity decisions.

Its flagship question is:

> How do we resolve noisy records at scale without all-pairs comparison, and how can we prove which pipeline stage made each labelled truth succeed or fail?

Concord is intentionally complementary to Relay:
- Relay: authority under distributed failure.
- Concord: identity under ambiguity.

---

## Architecture

```text
Raw Records
    |
    v
Schema Validation + Logical Dataset Identity
    |
    v
Versioned Normalization
    |
    v
Retrieval View Materialization
    |
    v
Bounded Multi-Lane Retrieval
    |
    +--> Lane Rescue / Retrieval Frontier
    |
    v
Provenance-Aware Candidate Graph
    |
    v
Typed 59-Feature Evidence Engine
    |
    v
Thin Scorer Interface
    |
    v
LightGBM Reference Scorer
    |
    v
Global Target Ownership
    |
    v
Explicit Candidate Disposition / Set Decoder
    |
    v
Zero / One / Many Resolution Sets
    |
    +--> Resolution Evidence Capsules
    +--> Failure Atlas
    +--> Cohort / Drift Lens
    +--> Stability-vs-Confidence Study
    |
    v
Content-Addressed Experiment + Artifact Lineage
```

---

## Evidence Plane

Every stage emits both:
1. the data product; and
2. enough compact metadata to explain/reproduce it.

Evidence identities form a lightweight DAG:

```text
dataset
  -> normalized dataset
     -> retrieval config + candidate graph
        -> feature schema + feature table
           -> model artifact + scores
              -> ownership policy
                 -> decoder config
                    -> resolutions
                       -> evaluation / benchmark report
```

Every edge is identified by content/config fingerprints, not by machine-local paths.

---

## Industry-aligned benchmark plane

Concord reports the full system, not only model F0.5.

### Retrieval
- Pair Completeness / truth recall
- Recall@1/5/10/20
- Reduction Ratio
- candidate density distribution
- zero-candidate rate
- lane rescue / overlap
- recall-vs-candidate Pareto frontier

### Scoring
- AUROC/AUPRC
- log loss
- Brier/calibration
- ranking diagnostics

### Ownership
- contention
- ownership loss
- rival margins

### Resolution
- Macro F0.5
- exact-set accuracy
- zero/single/multi-match cohorts

### Robustness
- same/cross-script
- OOD country
- unseen entity
- corner-case
- missingness

### Operations
- S1/sec
- candidate pairs/sec
- wall time
- CPU time
- peak RSS
- disk IO / artifact sizes

### Reproducibility
- repeat hashes
- environment identity
- code/config/data lineage

---

## Flagship research surfaces

### 1. Retrieval Frontier
Optimize recall against candidate cost, runtime and memory.

### 2. Lane Rescue Matrix
Measure which retrieval lane uniquely recovers each truth and at what candidate cost.

### 3. Cross-Script Retrieval Challenger
Test transliteration at retrieval time, directly addressing the historical gap where transliteration existed only in features.

### 4. Adaptive Candidate Budget
Optional bounded challenger allocating K by query ambiguity; never replaces fixed K without measured Pareto benefit.

### 5. Resolution Evidence Capsule
A compact explanation record for a single S1 decision.

### 6. Failure Atlas
Stage-by-cohort map of where labelled truths fail.

### 7. Stability vs Confidence
Test whether multi-stage structural fragility predicts wrong resolution sets better than raw model confidence.

### 8. Drift Lens
Compare source distributions, lane reliance, candidate density and failure mixtures across countries/scripts/benchmark variants.

---

## Six top-level CLI verbs

```text
concord inspect
concord retrieve
concord train
concord resolve
concord evaluate
concord benchmark
```

Feature richness lives beneath these verbs; top-level CLI sprawl is prohibited.

---

## Public benchmark strategy

### Synthetic
Committed, deterministic, exhaustive.

### WDC Products
Primary public quality benchmark because it explicitly exposes:
- corner cases;
- unseen test entities;
- varying development-set size.

### WDC large-scale product corpus
Optional scale track for candidate-generation/resource experiments.

External systems such as Splink and Ditto may be comparators only under same-split controlled runs.

---

## Legacy boundary

`src/concord/legacy_amazon/` is historical authority, not new application code.

Do not:
- modernize it;
- make it cross-platform;
- rewrite its provenance;
- change historical outputs;
- erase failed experiments.

Use it for:
- parity;
- definitions;
- architecture lineage;
- evidence.

---

## Scientific rules

- no invented benchmark values;
- no template metrics that look measured;
- no improvement claim without a class-D run manifest;
- no "world first";
- no "SOTA" without a controlled public comparison;
- no p>0.05 = equivalence;
- no public/private evidence conflation;
- negative/null experiments remain first-class evidence.

---

## V1 non-goals

- LLM matching for résumé value;
- vector DB without benchmark justification;
- Spark/Ray/Kafka/Kubernetes;
- Relay-like leases/consensus;
- AutoML;
- giant proof objects;
- event-sourced entity history;
- complex human-review product UI;
- Amazon private-data redistribution.

A future amendment may relax a non-goal only with measured evidence.

---

## Build gates

C1 — contracts, normalization, fingerprints, manifests, inspect, CI  
C2 — retrieval, provenance, Recall@K, lane rescue, frontier, public retrieval benchmark  
C3 — 59 features, LightGBM, ownership, decoder, calibration, failure attribution, evidence capsules  
C4 — cross-script challenger, stability, drift, adaptive-K experiment, benchmark suite, release

Detailed gate acceptance is in `PROPOSED_IMPLEMENTATION_PLAN_V1_1.md`.

---

## Final quality bar

Concord is complete only when an interviewer can ask:

- Why did this pair exist?
- Why did this pair score highly?
- Why did this source own the target?
- Why did the decoder accept/reject it?
- Which lane uniquely rescued it?
- How much candidate cost bought that recall?
- Which cohorts fail?
- Is confidence calibrated?
- Does structural stability add predictive signal?
- Can you reproduce the exact result?
- What changed between two experiments?
- What did the challenger cost?

…and the answer comes from artifacts, not memory.
