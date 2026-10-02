# Concord Architecture Amendment 001
## Contract correctness, benchmark alignment, and flagship feature expansion

**Applies after:** `3aa3211` — *Freeze Concord evidence-centric architecture*  
**Amends:** `docs/CONCORD_ARCHITECTURE_FREEZE_V1.md` and the proposed C1–C4 contracts  
**Status:** **AUTHORITATIVE FOR NEW CONCORD IMPLEMENTATION**  
**Legacy baseline:** `1133bfda496e2be59623fe154ec3dac45c13361f` (`amazon-ml-2026-final`) remains immutable.

---

## 1. Why this amendment exists

The original freeze selected the correct architecture: Evidence-Centric Entity Resolution (Option B) with a scoped stability extension. That decision is retained.

This amendment does **not** redesign Concord. It removes ambiguities that would otherwise become implementation bugs and expands the benchmark/evidence surface so the final project demonstrates modern IR/ML-systems engineering rather than only a cleaned competition pipeline.

The following are unchanged:

- the legacy Amazon pipeline is preserved verbatim;
- five-view bounded sparse retrieval remains the historical reference;
- `retrieval_view_mask` remains the historical provenance primitive;
- the 59-feature schema remains the historical feature reference;
- LightGBM remains the first-class reference scorer;
- global target ownership remains the historical arbitration baseline;
- `0.640` remains the historical decision threshold baseline;
- Parquet is the bulk table format;
- canonical JSON is the metadata/evidence format;
- Concord remains a single-node IR/ML-systems project, not a Relay-like distributed system;
- no unsupported historical metric may be promoted.

---

## 2. Authority and supersession

If this amendment conflicts with an older frozen document, this amendment wins for **new Concord**.

The legacy historical implementation is never rewritten to conform to these contracts.

Implementation agents must read in this order:

1. `docs/CONCORD_ARCHITECTURE_FREEZE_V1.md`
2. `docs/CONCORD_ARCHITECTURE_AMENDMENT_001.md`
3. `docs/CONCORD_FLAGSHIP_SPEC_V1_1.md`
4. `docs/audit/PROPOSED_DATA_CONTRACT_V1_1.md`
5. `docs/audit/PROPOSED_EXPERIMENT_AND_BENCHMARK_CONTRACT_V1_1.md`
6. `docs/audit/PROPOSED_IMPLEMENTATION_PLAN_V1_1.md`

---

## 3. Mandatory contract corrections

### A001-01 — Missing and empty values are distinct

The old proposed dataclass used `str` while simultaneously claiming missing and empty values were distinguishable.

New rule:

- raw missing text is `None`;
- present-but-empty text is `""`;
- normalization preserves `None`;
- normalization of `""` is `""`;
- retrieval adapters may map `None` to an empty vectorizer input **only at the retrieval boundary**, while retaining an explicit missingness flag;
- no `"nan"`, `"NULL"`, `"None"` or other string sentinel represents missingness.

Historical `fold()` compatibility applies to **non-null strings**. Historical behavior for `None` is not adopted as the new semantic contract.

### A001-02 — Entity IDs are opaque

New Concord must not assume IDs look like `S1-xxxx`.

`entity_id` is an opaque, non-empty string. `source` is authoritative and separately validated.

### A001-03 — Country is an opaque dataset label

Historical values such as `US`, `India`, and `France` are preserved as dataset labels.

New Concord does not falsely claim these are ISO codes. Public datasets may omit country entirely.

### A001-04 — Compact-name is a retrieval representation

`name_compact` is removed from `NormalizedEntity`.

Base normalization remains exactly:

`NFKD -> remove combining marks -> casefold`

for non-null text.

Whitespace stripping for the compact lane belongs to C2 retrieval view construction.

### A001-05 — Frozen containers must actually be immutable

`frozen=True` is insufficient when fields contain mutable `dict` or NumPy arrays.

New contracts use immutable tuples / fixed records at object boundaries. Batch numeric execution may use NumPy/PyArrow internally, but mutation cannot leak through the public data contract.

### A001-06 — Scoring, ownership, and decoding are separate types

`ScoredCandidate` may not contain fields produced by later stages.

The required transition is:

`RetrievalCandidate -> FeatureRow -> ScoredCandidate -> OwnershipResult -> CandidateDisposition -> ResolutionDecision`

This is an architectural invariant.

### A001-07 — Resolution evidence stores raw signals, not a pre-decided "stable" label

The old `is_stable: bool` field is removed.

C4 must learn/evaluate whether stability variables predict errors; the contract must not encode the answer in advance.

### A001-08 — Zero-match evidence uses explicit undefined values

For zero-match decisions, values such as minimum accepted-target lane count, threshold margin, or ownership margin may be undefined.

Use `None`, never NaN or magic sentinels.

---

## 4. Failure attribution semantics

Concord performs **stage attribution**, not philosophical causal proof.

The authoritative statement is:

> Failure attribution identifies the earliest policy-relevant stage at which a labelled truth can no longer reach the final output under the frozen configuration. It is deterministic stage attribution, not proof of the underlying causal mechanism.

Primary stages:

1. `RETRIEVAL`
   - a labelled truth pair never entered the candidate graph.

2. `SCORING`
   - the truth pair was retrieved but its score is not admissible under the frozen score/threshold policy.
   - for the historical baseline, this includes a truth score below `0.640`.

3. `OWNERSHIP`
   - the truth pair is score-admissible but the target is assigned to another S1 under deterministic global ownership.

4. `DECODING`
   - the truth pair is score-admissible and owns the target, but the set-level policy excludes or mis-emits it.
   - in the historical fixed-threshold baseline this stage may be rare; future set policies may make it more relevant.

5. `AMBIGUOUS_OR_INSUFFICIENT_EVIDENCE`
   - reserved for label/data conditions that genuinely prevent a unique stage attribution.
   - it is not a generic fallback.

Orthogonal tags remain independent:

- `CROSS_SCRIPT`
- `COUNTRY_OOD`
- `TRANSLITERATION_DEPENDENT`
- `NORMALIZATION_SENSITIVE`
- `SINGLE_LANE`
- `ZERO_MATCH`
- `MULTI_MATCH`
- `HIGH_AMBIGUITY`
- `UNSEEN_ENTITY`
- `CORNER_CASE`

False-positive attribution follows the same policy-gate idea:
- a non-match receiving an admissible score is principally a `SCORING` error unless a later decoder rule admits a score-ineligible pair;
- ownership and decoder context are preserved as diagnostics/tags.

---

## 5. Fingerprint semantics

### Dataset fingerprint

New Concord dataset identity is **logical-content identity**, not physical-file identity.

Requirements:

- SHA-256;
- schema version included;
- records canonicalized by `(source, entity_id)`;
- duplicate `(source, entity_id)` keys rejected;
- explicit null encoding distinct from empty string;
- canonical UTF-8 bytes;
- independent of JSON dictionary insertion order;
- independent of Parquet row order;
- independent of OS path and newline convention;
- no timestamps or machine-local absolute paths in digest input.

Therefore:

`same logical records + different row order -> same dataset fingerprint`

`None != ""`

`one changed value -> different fingerprint`

### Split fingerprint

Split identity includes:

- split schema version;
- purpose/name;
- canonical sorted entity membership;
- optional cohort metadata;
- dataset fingerprint.

Membership changes must change the split fingerprint.

---

## 6. Experiment-manifest correction

A run manifest is **not** itself a JSON Schema.

Instances use:

`"schema_version": "concord.experiment.v1"`

If a formal JSON Schema is provided, it lives as a separate `.schema.json` artifact and may declare JSON Schema Draft 2020-12.

The canonical example must not contain invented measurements.

No template may include plausible fake values for:

- Recall@K;
- cross-script F0.5;
- runtime;
- peak memory;
- throughput;
- calibration;
- stability performance;
- country metrics.

Unmeasured fields are absent or `null`.

Every metric must carry or inherit:

- metric name;
- population/split/cohort;
- unit;
- direction if relevant;
- evidence class;
- producing artifact/run identity.

---

## 7. Cross-platform acceptance

"Windows + Linux compatible" requires evidence from both platforms.

C1 is not considered fully closed from a Windows-only local run.

Acceptable closure:

- native Windows local test pass; and
- Ubuntu CI or explicit Linux/WSL test pass.

A small CI matrix is preferred.

Legacy `fork` code is exempt because it remains frozen historical source.

---

## 8. Public/private parity policy

Every gate has two possible evidence levels:

### PUBLIC_PASS
Achieved with committed synthetic fixtures and/or public benchmarks.

### PRIVATE_PARITY_PASS
Optional stronger evidence available only when authorized private Amazon data/model artifacts are supplied locally.

A public release must never pretend `PUBLIC_PASS` implies private historical rerun parity.

C3 public acceptance requires schema/function parity on public/reference fixtures.

Exact historical probability parity is a **private reproduction claim**, not a public C3 blocker.

---

## 9. Industry benchmark alignment

Concord's benchmark design is aligned with real entity-resolution practice, while preserving its own architecture.

### Blocking / candidate generation

Modern record-linkage systems treat candidate reduction as a first-class engineering problem because pair counts grow quadratically. Concord therefore reports both truth capture and comparison cost.

Required retrieval metrics:

- truth-pair Recall / Pair Completeness;
- Recall@1 / 5 / 10 / 20 where ranked semantics exist;
- candidate-pair count;
- candidates per S1: mean / p50 / p90 / p99 / max;
- zero-candidate S1 rate;
- Reduction Ratio relative to the eligible Cartesian universe;
- wall-clock runtime;
- peak RSS;
- bytes written / read when measurable.

### Public benchmark tracks

#### Track P0 — Synthetic contract suite
Always committed. Tiny, deterministic, exhaustive, fast.

#### Track P1 — WDC Products
Preferred public quality benchmark.

Use its dimensions explicitly:
- corner-case prevalence;
- unseen entities in test;
- development-set size.

Report the exact WDC variant. Do not collapse multiple variants into one score.

#### Track P2 — WDC large-scale product corpus
Optional scale/retrieval engineering track.

Use only where resource limits permit, with exact subset/full-corpus scope recorded.

### External comparator policy

Potential comparators include:
- deterministic/rule baseline;
- Splink probabilistic linkage baseline;
- a transformer matcher such as Ditto where compute/licensing permit.

Comparator results are valid only when rerun on the same split/variant with the same candidate boundary. Literature numbers are contextual references, never direct leaderboard claims for Concord.

---

## 10. Flagship feature suite

All features remain under the six frozen top-level CLI verbs.

### `concord inspect`

Sub-surfaces:
- `profile` — counts, missingness, scripts, countries, field lengths;
- `schema` — schema validation and version;
- `fingerprint` — dataset/split identities;
- `drift` — compare two dataset profiles;
- `lineage` — show artifact-parent DAG.

### `concord retrieve`

Sub-surfaces:
- `run` — bounded multi-lane candidate generation;
- `frontier` — Recall vs candidate-cost Pareto frontier;
- `lane-rescue` — per-lane unique truth recovery and overlap;
- `ablate` — leave-one-lane-out candidate-availability analysis;
- `challenge-transliteration` — controlled transliteration retrieval challenger;
- `challenge-adaptive-k` — experimental adaptive candidate budget.

### `concord train`

Sub-surfaces:
- `fit` — reference LightGBM;
- `negatives` — retrieval-derived negatives;
- `calibrate` — score calibration and reliability analysis;
- `fingerprint` — model/config identity.

### `concord resolve`

Sub-surfaces:
- `run` — scoring -> ownership -> decoding;
- `explain` — one S1 resolution evidence capsule;
- `export-evidence` — machine-readable evidence records;
- `replay` — rerun a manifest-identified configuration on the same compatible inputs.

### `concord evaluate`

Sub-surfaces:
- `quality` — Macro F0.5 and set-level metrics;
- `cohorts` — same/cross-script, country, unseen, corner-case;
- `failures` — stage-attribution atlas;
- `policy` — threshold / precision / recall / zero-match frontier;
- `calibration` — Brier, ECE/reliability, calibration slope/intercept where valid;
- `stability` — pre-registered S1-level stability-vs-confidence study.

### `concord benchmark`

Profiles:
- `smoke` — synthetic;
- `public` — WDC public quality track;
- `scale` — larger candidate-generation/resource track;
- `compare` — same-config comparisons between retrieval/model challengers.

---

## 11. Flagship innovations

These are **experiments**, not pre-claimed successes.

### Innovation I1 — Evidence Plane

Every major pipeline artifact carries:
- parent fingerprints;
- producing config hash;
- code commit;
- schema version;
- stage;
- evidence class.

This forms a lightweight content-addressed provenance DAG without event-sourcing.

### Innovation I2 — Retrieval Frontier

Treat retrieval as a multi-objective system:
- maximize truth capture;
- minimize candidate comparisons;
- minimize memory/runtime.

A candidate-generation change is promoted only if it is Pareto-nondominated or passes a pre-registered utility gate.

### Innovation I3 — Lane Rescue Matrix

For each retrieval lane:
- truths uniquely rescued;
- truths shared with each other lane;
- candidates added;
- marginal recall per million comparisons.

This turns `retrieval_view_mask` into actionable retrieval science rather than a decorative bitmask.

### Innovation I4 — Cross-Script Retrieval Challenger

Historical transliteration existed only in features.

New Concord may test one or more transliterated retrieval lanes as a challenger.

Promotion requires measured improvement on a labelled cross-script cohort with the exact candidate-cost overhead reported.

A null or negative result is preserved.

### Innovation I5 — Adaptive Candidate Budget Challenger

Optional C4 challenger.

Instead of fixed K for every query, allocate a bounded candidate budget using pre-scoring query signals such as:
- missingness;
- token length;
- script mismatch;
- lane agreement;
- retrieval score concentration.

It must never silently replace the frozen fixed-K baseline.

Promote only if it improves the recall/candidate-cost frontier under a pre-registered cap.

### Innovation I6 — Resolution Evidence Capsule

For one S1 decision, emit a compact human- and machine-readable record containing:
- accepted set;
- top rejected competitors;
- lane provenance;
- score;
- ownership result/rival margin;
- threshold margin;
- tags/cohort membership;
- dataset/model/decoder fingerprints.

This is intentionally smaller than a "proof object".

### Innovation I7 — Failure Atlas

Aggregate stage attribution into:
- stage counts;
- cohort-by-stage matrix;
- lane dependence;
- score-margin distributions;
- ownership contention distributions;
- zero-match/multi-match breakdown.

### Innovation I8 — Stability vs Confidence Study

Primary unit: S1 resolved set.

Store raw stability features:
- accepted-target lane redundancy;
- candidate-availability under single-lane removal;
- ownership margins;
- threshold margins;
- candidate ambiguity;
- candidate-set density.

Do **not** store a hard-coded `is_stable`.

Compare against confidence baselines using:
- AUROC;
- AUPRC on error class;
- risk-coverage;
- risk at fixed coverage;
- bootstrap confidence intervals.

`p > 0.05` means **no clear evidence of difference**, not "confirmed equivalence".

Equivalence may be claimed only with a pre-declared equivalence margin and appropriate test.

### Innovation I9 — Drift Lens

Compare datasets/cohorts using:
- missingness shift;
- script distribution;
- field-length/token distribution;
- candidate density;
- retrieval-lane reliance;
- score calibration;
- error-stage mixture.

The first use case is the historical US/India -> France distribution shift.

---

## 12. C1–C4 amendments

### C1 — Foundation + Contracts

Add:
- explicit `None` vs `""`;
- opaque IDs;
- optional country label;
- row-order-independent logical fingerprints;
- separate JSON schema artifact;
- deterministic manifest serializer;
- Windows local + Linux CI/WSL pass;
- artifact lineage primitives;
- `concord inspect profile|schema|fingerprint`.

Do not add retrieval.

### C2 — Retrieval + Provenance

Add:
- immutable lane evidence;
- no `999` sentinel in new contracts;
- candidate density + Reduction Ratio;
- lane-rescue matrix;
- leave-one-lane-out candidate-availability analysis;
- WDC Products adapter/benchmark configuration where feasible;
- retrieval frontier report.

Transliteration retrieval remains a challenger.

### C3 — Evidence + Model + Ownership + Decoder

Add:
- strict type separation between scored / ownership / disposition;
- calibration report;
- public parity vs private parity distinction;
- failure-stage engine using the precedence in this amendment;
- Resolution Evidence Capsule.

Do not require exact historical model probabilities for PUBLIC_PASS.

### C4 — Cross-Script + Stability + Scale + Release

Add:
- cross-script retrieval challenger;
- optional adaptive-K challenger;
- WDC benchmark matrix;
- drift lens;
- failure atlas;
- stability-vs-confidence with bootstrap confidence intervals;
- benchmark profiles with exact hardware/config scope;
- self-contained flagship evidence report generated from manifests.

---

## 13. Claim rules added by this amendment

Do not claim:
- "industry leading";
- "production grade";
- "state of the art";
- "world first";
- "self-auditing improves accuracy";
- "adaptive K improves efficiency";
- "transliteration retrieval improves recall";
- any benchmark number not tied to a run manifest.

Safe wording after implementation must always identify:
- dataset;
- split/variant;
- metric;
- config;
- evidence class.

---

## 14. Non-goals wording correction

The old phrase "permanently out of scope" is replaced by:

> **V1 non-goals.** A future architecture amendment may introduce a currently excluded technology only after profiling or controlled experiments show a concrete need.

V1 still excludes:
- LLM matching for résumé value;
- vector DBs without benchmarked benefit;
- Spark/Ray/Kafka/Kubernetes;
- AutoML;
- Relay-like leases/consensus;
- event-sourced entity-history systems;
- heavyweight human-review product UI;
- private Amazon-data redistribution.

---

## 15. External industry/research basis

This amendment uses external references only for architecture/benchmark inspiration; they do not upgrade historical Concord evidence.

- **AWS Entity Resolution:** modern managed ER exposes configurable matching workflows, normalization, rule/ML approaches, confidence outputs, job history, and incremental processing.
- **Splink:** blocking/candidate generation is treated as the dominant control on comparison volume; blocking quality is a trade-off between capturing true matches and the number of comparisons produced.
- **WDC Products:** public benchmark explicitly varies corner cases, unseen test entities, and development-set size with split-disjoint records.
- **WDC large-scale product corpus:** provides a much larger public scale context for product matching.
- **Zingg:** explanation/traceability of why records cluster is a practical ER product concern.
- **Ditto:** establishes a strong neural entity-matching reference and demonstrates large-scale company matching, but Concord does not adopt a transformer by default.

These references motivate benchmark design and diagnostic surfaces; Concord's claims remain tied to Concord's own manifests.

---

## 16. Final implementation rule

Concord should feel extreme because its **evidence surface is deep**, not because it contains random infrastructure.

The project must be able to answer, from artifacts:

1. What did we compare?
2. Why was this pair retrievable?
3. Which lane rescued it?
4. What evidence did the scorer see?
5. Why did this S1 win or lose ownership?
6. Why did the decoder emit this set?
7. Which subsystem lost each labelled truth?
8. Which cohorts fail disproportionately?
9. What was the recall/candidate-cost frontier?
10. Can the exact run be reproduced from fingerprints and config?
11. Did a challenger actually beat the frozen baseline?
12. How much CPU, memory, disk and wall time did it cost?

That is the flagship bar.
