# Concord Resolution Explorer — Product Specification V1

Specification date: 4 October 2026 (Asia/Calcutta). Individual project by Adithya Sanjeevi.

Audited repository: `ADITHYA-SANJEEVI/concord-entity-resolution`.
Authoritative audited HEAD: `cd3e8646d6f1b92a425db4b86af6be4004ba3a2f`.
Baseline tag: `concord-neutral-public-baseline`.
Specification branch: `product/resolution-explorer-spec`.
Recorded evidence producer: `0ead99612ce93d47e51d748d3ecc01a026a92864`.

This is a specification, not an implemented frontend or inspection service. It defines one product and its staged delivery. No backend, fixture, metric or C1–C4 evidence change is required by this document. Wireframes below use rendered spatial tables rather than character drawings; widths, placement, hierarchy and collapse behavior are normative.

## 1. Executive product thesis

Concord Resolution Explorer is an evidence workbench for reconstructing entity-resolution decisions in a declared run. Its primary object is a **source case within a specific dataset, split, model, platform and recorded run**, not a source ID in isolation. The user selects a candidate and follows its retrieval evidence, ordered numeric features, learned score, global ownership outcome, decoder disposition and final emitted set. Scientific evaluation and artifact lineage establish what was measured and what can be inspected. The product explains policy execution through recorded structure; it does not claim to explain model causality or real-world identity beyond labels.

The primary workspace is appropriate because Concord's strongest differentiation is separation of retrieval, learning and policy. A general dashboard would obscure that separation. Use the metaphor **case dossier with an evidence ledger**: precise, calm, dense and read-only. Keep the scientific experiment context continuously visible. No landing-page hero, generic overview dashboard, model-promotion workflow or manual match editing belongs in V1.

The defining visual is an **aligned Candidate Resolution Ledger**, an equivalent to the proposed Candidate Resolution Graph. It preserves the source-to-candidate relationship while displaying independent policy columns. A small selected-target contention diagram is supplementary and conditional. Do not make a radial or free-layout graph the primary navigation mechanism.

## 2. Central product question and epistemic boundary

**Why did Concord resolve this entity this way?**

Every answer must name the run and supporting evidence. The product can answer “which policy gates were satisfied?” and “where did a labelled error first fail the attribution policy?” It cannot answer “which feature caused the model score?” with current evidence. A high score means a learned pair probability, not verified identity, acceptance, confidence in the entire set or a calibrated real-world guarantee.

The six visible stages are RETRIEVAL, FEATURES, SCORING, OWNERSHIP, DECODING, RESOLUTION. FEATURES is inspectable but is not a separate failure-attribution category. Evaluation is an overlay after resolution; an accepted pair can be a false positive. Missing evidence is a coverage or validation problem, not a model failure stage.

Separate three independent labels in the context ribbon:

| Dimension | Current value/behavior | Future boundary |
|---|---|---|
| Data origin | `SYNTHETIC FIXTURE`, derived from `SYNTHETIC_PUBLIC` manifests | Schema permits PUBLIC/PRIVATE_LOCAL, but no corresponding evaluated corpus is supplied here |
| Evidence delivery | `PUBLIC RECORDED EVIDENCE` for committed bundles; recorded local artifacts when actually attached and validated | `LIVE LOCAL RUN` is future capability, never a selectable working mode in Slice 1 |
| Coverage | Complete stages, bounded examples, summary only, or partial evidence, computed per resource | A badge cannot turn absent files into complete evidence |

Synthetic and recorded are not mutually exclusive modes: the current recorded evidence is synthetic. Never provide a switch that relabels the same records as live or production.

## 3. Repository capability audit

### 3.1 Audit scope and evidence levels

Read README, ARCHITECTURE, all three PASS usage guides, REPRODUCIBILITY and all three root evidence reports. Inspect contracts, normalization/identity/storage, retrieval engine and diagnostics, feature definitions, modeling/mining, inference, evaluation, research definitions/experiments/reports/statistics/scale, reference numerical functions and artifacts, CLI inspection/explain/export, experiment schema and retention scripts. Review relevant foundation, retrieval, feature, training/storage, resolution, CLI, research and evidence test assertions. Existing test results are recorded evidence, not a new test execution by this documentation task. No historical checkout is used.

Four audit labels apply throughout:

| Label | Meaning |
|---|---|
| C | Bytes or structured fields committed at audited HEAD |
| L | Implemented local output/CLI capability; full producing output bytes are absent from this checkout |
| D | Deterministic read-only presentation derivation from supplied C/L inputs; not a newly measured result |
| G | BACKEND READ GAP; proposed access or absent data, not existing functionality |

“Implemented” and “publicly inspectable now” are different claims. `outputs/` and Parquet/model artifacts are ignored. The public bundles embed manifests, summaries and selected examples, not full stage tables.

### 3.2 Capability and evidence inventory

| Capability | Actual code/evidence | Level and product consequence |
|---|---|---|
| Typed raw entities, source and country | `contracts.py:EntityRecord`; `storage.py`; synthetic TSV/generators | C contracts/fixtures; C4 examples embed raw sources/targets; arbitrary run records require L |
| Null/empty and normalized text | `NormalizedEntity`; `normalization.py`; storage schemas | Preserve null and empty separately; recorded normalized bytes are L; do not reconstruct them and call them recorded |
| Country-eligible sparse retrieval | `retrieval/baseline.py:retrieve, RetrievalConfig, FitEvidence` | C behavior; L full graph/fit tables; candidate snippets are C |
| Five lanes and budgets | name/compact/address/combined/reverse, budgets 5/5/5/10/8 | C; reverse is per-target incoming query budget, not an outgoing per-source cap |
| Ordered 59 features | `features/reference.py:REFERENCE_SCHEMA, FeatureRow`; `c3_storage.py` | C names/definitions/order; L per-pair values; store float64, convert at float32 model boundary |
| Learned scoring | `modeling/scorer.py`, `training.py`; `research/scorers.py` | C reference and logistic implementations; C selected scores; L model weights/full scores |
| Global target ownership | `inference/resolution.py:global_ownership`; `OwnershipResult` | C rule and selected rival evidence; L full competitors |
| Frozen decoder and final sets | `DecoderConfig`, `decode`, `CandidateDisposition`, `ResolutionDecision` | C .640 rule and selected emitted sets; L complete decision tables |
| Explain and evidence export | `c3_cli.py:resolve_command` | L file-backed CLI: capsule plus at most five rejected candidates; not an HTTP API or full case-detail response |
| Quality/calibration | `evaluation/quality.py`; root reports/bundles | C aggregate reports; compact retention removes per-query metrics |
| Deterministic attribution | `evaluation/failures.py`; `c3_contracts.py:STAGES` | C exact semantics, counts and examples; L all attribution rows |
| C4 Failure Atlas | `research/reports.py:atlas, ATLAS_SCHEMA` | C reference summary: 21 errors, 7 examples per platform; L all 21 entries and bulk stages |
| Twelve diagnostic definitions | `research/definitions.py`, `experiments.py`; C4 bundle | C definitions, results, comparisons, cohorts and movements |
| Perturbation reruns/repeats | `research/fixtures.py`, `experiments.py` | C change counts/IDs and repeat flags; L before/after decision observations |
| Scale profiling | `research/scale.py`, `ScaleObservation`; C4 bundle | C medians/ranges/RSS, counts/config/environment; L repetition-level observations |
| Provenance and verification | `metadata.py:ArtifactLineage, validate_manifest, validate_lineage`; `c3_cli.py:verified_run` | C manifests and declared DAG; L physical verification of original bytes |
| Search/browser read service | CLI parsers, package dependencies and source inventory | G: no HTTP inspection API, case index, artifact-query endpoint or live run service |

Evidence files: `docs/evidence/PASS_A_RUNS.json` and PASS_B have schema `concord.pass-a-evidence.v2` / `concord.pass-b-evidence.v2`; PASS_C has `concord.pass-c-evidence.v1`. Both `windows` and `ubuntu_wsl` observations are present. `scripts/retain_pass_c_evidence.py:compact` explicitly removes `per_query`, `risk_coverage`, `raw_confidence_diagnostics` and `origin_by_pair`. The UI must not recreate those as observations from aggregates.

### 3.3 Fixed decision semantics

1. Entity identity is `(source, entity_id)`. Candidate identity is `(s1_id, target_id)` inside the declared population. S2/S3 target ID collisions are rejected.
2. Retrieval blocks by exact country equality; null-country matches null-country and differs from empty-country. It has no all-pairs fallback for empty vocabulary. Small synthetic profiles explicitly relax DF settings; they are not reference-profile runs.
3. Each lane has its own similarity and one-based rank. Reverse ranks queries around a target. A candidate absent from a lane has no C2 rank; numeric feature rank `999` is a model compatibility sentinel only. Feature graph ranks are pre-model cosine ranks, not learned ownership ranks.
4. Ownership groups all scored edges by target within the declared run population, sorts score descending and source ID ascending, and assigns a unique rank-1 owner. A winner's rival is the runner-up; a loser's rival is the winner. Singleton rival fields are null. Global means this declared population, not all datasets everywhere.
5. Decoder acceptance is exactly `is_owner AND score >= 0.640`. Canonical rejection: BELOW_THRESHOLD first, then LOST_OWNERSHIP. Accepted reason is NONE. SET_POLICY is reserved and cannot occur under current contract validation.
6. Final sets contain sorted unique target IDs. Empty, single and multi-target results are all valid. A target cannot be accepted by two sources.
7. Failure attribution follows Section 9 and does not use a generic “model explanation” string.

### 3.4 Evidence observations that must survive presentation

| Observation | Exact public evidence | Meaning |
|---|---|---|
| C3 test | 16 queries; macro F0.5 0.614583; exact-set accuracy 0.562500 | Tiny synthetic integration evidence |
| C4 reference | 133 test queries; macro F0.5 0.842105 | Invented recipe; shared templates |
| C4 logistic | Macro F0.5 0.864662; paired delta +0.022556 | Diagnostic comparison |
| Paired interval | Descriptive 95% interval [-0.015038, +0.067669], 1,000 bootstrap repetitions, seed 2026 | Includes zero; no established scorer winner, no equivalence conclusion |
| C4 reference errors | FN: retrieval 8, scoring 5, explicit ambiguity 1; FP: scoring 7; ownership/decoding zero | 21 error pairs, not 21 necessarily distinct sources |
| C3 ownership error | `test-own-z` → `test-own-target` | One recorded ownership FN in C3; do not invent a C4 ownership FN |
| C3 ownership tie example | `test-amb-z` → `test-amb-target`, score 0.9998072758773955, rival `test-amb-a` at same score, owner rank 2 | Decoder LOST_OWNERSHIP; labelled error attributed to explicit ambiguity |
| C4 similarly named example | `test-amb-z` score 0.13914703328081957, threshold 0.640 | Different dataset/model; BELOW_THRESHOLD disposition, explicit ambiguity attribution |

Values shown to six decimals are rounded displays of retained precision. Decisions use original values. Lane cosine evidence permits tiny numerical overshoot above 1; never clamp or show it as a pair probability. Formatting may show approximately 1.000000 with exact detail available.

## 4. User/operator jobs-to-be-done

| Job | Start | Successful answer |
|---|---|---|
| Audit a decision | Source deep link or indexed example | Source, final set, selected candidate gates and coverage are unambiguous |
| Diagnose a labelled miss | Failure Atlas error pair | Attribution category, truth/accepted sets, evidence and precedence are visible |
| Inspect contention | LOST_OWNERSHIP edge or rival link | Winner/rival ID, score, rank, tie-break and declared population are visible |
| Examine feature evidence | Selected candidate, Features tab | Exact schema order, definition and recorded values, or a precise gap |
| Compare an experiment | Experiment catalogue | Same-population metric delta, interval, changed definition and diagnostic status |
| Assess resource cost | Scale workload | Measurement scope, repetitions, timing and process memory limits |
| Verify a claim | Metric/candidate evidence reference | Producer and artifact occurrence, declared parents and byte availability |

Primary users are the project author, an engineering reviewer and an ML evaluation reviewer. V1 has no account, organization, customer, analyst assignment, approval queue or editing role model.

## 5. Product information architecture

Five global destinations: Explorer, Failures, Experiments, Scale, Evidence. The shell contains a compact wordmark, these links, global search and the context ribbon. No separate Runs page: manifests are run context and evidence records; experiments are their scientific views. No separate Models, Datasets or Targets section: inspect them through evidence and scoped search until richer access exists.

`/explorer` is a useful case-entry route, not a dashboard. It lists inspectable cases, their run scope and coverage. Opening the app goes here. All required detail routes remain. Artifact details open as full routes with the same shell; inline previews never replace durable links.

Changing a run must not silently preserve an ID-matched case as if it were the same observation. Offer “Open this ID in selected run” only after availability is checked. Keep platform observations separate even when logical decisions agree.

## 6. Route map

| Route | Purpose | Default state |
|---|---|---|
| `/` | Redirect | `/explorer` |
| `/explorer` | Scoped case catalogue | Available recorded examples; explicitly bounded |
| `/explorer/:source_id` | Resolution Explorer | Selected case within `run`; candidate optional |
| `/failures` | Failure Atlas aggregate and case browser | Reference/test in chosen C4 run; C3 selectable |
| `/experiments` | Diagnostic experiment catalogue | Definition-order table, not score ranking |
| `/experiments/:experiment_id` | Scientific evidence and reference comparison | Test tab; explicit run context |
| `/scale` | Controlled workload observations | One platform, pipeline stage, available sizes |
| `/evidence` | Artifact occurrence browser | Declared manifest artifacts with availability |
| `/evidence/:artifact_id` | Artifact occurrence and lineage | Identity, producer, parents, coverage |

`:experiment_id` is a UI handle for a manifest plus a definition, because the C4 manifest contains all twelve definitions. It is not a claim that each definition has its own backend manifest. `:artifact_id` identifies a producing occurrence, not only a shared physical hash. Handle rules and query parameters are in Section 19.

## 7. Resolution Explorer detailed design

### 7.1 Large-desktop wireframe

At viewport width at least 1440px, use 16px outer margins, a 48px shell, a 40px context ribbon and a 64px case header. Body is one bordered workbench, with a 256px left context pane, a flexible central pane of at least 560px and a 344px right trace pane. The evidence detail region spans center and right, initially 256px high and resizable between 180px and 45% of viewport height. It is a layout region, not a modal. Left context remains visible alongside it.

| Full-width shell | Explorer · Failures · Experiments · Scale · Evidence · Search |
|---|---|
| Full-width context ribbon | Synthetic fixture · Public recorded evidence · Run/platform/split/definition · Coverage |
| Case header | Source ID · emitted target IDs · zero/single/multi · labelled quality if available · Copy link |

| Left: source/context 256px | Center: candidates, flexible | Right: selected trace 344px |
|---|---|---|
| Source ID/S1; raw name/address/country; null/empty markers | Candidate Resolution Ledger; counts and coverage above rows | Selected target ID/source; target raw fields if present |
| Raw/normalized toggle, with availability | Target · lane chips · learned score · owner/rival · decoder disposition | Six stage sections; threshold comparison and owner status separate |
| Dataset/split; truth set collapsed under Evaluation | Shared row selection; filters/sort; visible-row count | Rival link and tie-break; final membership; evidence references |
| Context artifacts and limitations | Lower detail region starts below candidate viewport | Detail region spans center and right |
| Source context stays in place | Retrieval / Features / Raw / Provenance tabs | Same selected candidate and run scope |

No decorative summary cards. Emitted target IDs are the answer at the top; candidate scores are supporting evidence. For more than four emitted IDs, show four and an accessible “Show all N” disclosure, not an opaque “+N” alone.

### 7.2 Source and candidate behavior

Raw name/address are selectable text with wrapping and explicit `null (missing)` / `"" (empty)` labels. IDs are opaque, never prettified into organization names. Dataset country labels such as P0-SEEN are fixture labels, not actual geographic metadata. Source records absent from a bundle display the ID and “Raw source record not retained”; do not borrow a similarly named record from another fixture.

Candidate rows show target ID, target source, lane presence, learned score, ownership status/rank and decoder disposition. Optional compact target name is secondary, only when actually supplied. Default full-case ordering is learned score descending, target ID ascending. No rank-1 crown or “best match” label. Sorting does not change ownership or final sets. Sort/filter operates only on loaded evidence and announces its coverage.

Default selection is the first row under that canonical display order, regardless of acceptance; explicit `candidate` URL wins. Show “Highest displayed score” rather than “Best result.” Full resolution rows may include accepted targets below the first displayed page; header always uses the actual complete emitted set. For bounded snippets, label “8 of 63 candidates retained in this example” or “5 of 20 top rejected candidates retained”; never claim filtering across the omitted graph.

Clicking a row or target cell selects it and synchronizes ledger, right trace and lower details. Selecting does not expand every section or move keyboard focus away from the row. An explicit “Inspect details” action moves focus to the right-pane heading. Arrow navigation is specified in Section 22. A second candidate is not a second independent selection; V1 uses one selected pair and optional rival context.

### 7.3 Trace content and deterministic wording

| Stage section | Content | Allowed statement |
|---|---|---|
| Retrieval | Present lanes, similarity/rank, representation origin when retained | “Retrieved by name, combined and reverse” |
| Features | Schema/version and recorded values link | “59 ordered features; values not retained in this bundle” when absent |
| Scoring | Exact learned score, model identity, scorer type | “Recorded pair score 0.999807”; no fabricated feature contribution |
| Ownership | is_owner, owner_rank, rival ID/score/margin, policy | “Rank 2; tied score, source ID tie-break favors test-amb-a” when evidence proves it |
| Decoding | .640 threshold, signed margin, accepted flag, canonical reason | “Threshold satisfied; rejected: LOST_OWNERSHIP” |
| Resolution | Membership in recorded accepted set; overall decision kind | “Not emitted; source resolved to an empty set” |

When score is below threshold and ownership is lost, show both facts, but canonical rejection is BELOW_THRESHOLD. Missing stage evidence uses “Not retained” or “Unavailable”; it cannot be colored as passed or failed. Wording is fixed template assembly from evidence, not generated narrative.

A margin of zero is a tie, not absent data. A singleton's null rival means no competing edge in the recorded population, not low uncertainty. With rounded equal-looking scores, evaluate tie-break wording only using retained full precision. No threshold slider, “try a different score,” replay button or edit acceptance control.

### 7.4 Lower detail region

Retrieval tab uses a five-row lane table: lane, present/absent/unknown, one-based rank, similarity, direction, representation origin and reference. Absent means demonstrated absent in a complete candidate record; unknown means the record is missing. Explain reverse direction in visible copy. Display warnings/config separately from a candidate's provenance.

Features tab defaults to ordered schema rows with index 0–58, exact machine name, definition, recorded value and availability. Group shortcuts use existing ablation groups; they overlap conceptual information and do not define causal importance. Column 28 remains outside zeroed groups. Show pre-mask values versus effective zeroed inputs only when the experiment definition and recorded base values support that deterministic derivation; label it derived. Schema-only mode keeps values unavailable, never zeros. `f55`–`f58` retain their exact identifiers with readable definitions. Model missingness flags conflate empty/missing as declared; source raw text does not.

Raw tab displays the selected structured record fragments as plain selectable text, with source bundle path/JSON pointer or file occurrence reference. Escape all strings; no HTML interpretation. Provenance tab shows supporting occurrences and identity fields, retaining distinction between logical fingerprints and byte hashes. Each reference navigates to Evidence while preserving return context.

## 8. Candidate Resolution Graph equivalent: aligned ledger and contention inset

### 8.1 Decision

The proposed source fan-out is expressive for three targets, but poorly supports tens of candidates, independent policy stages, missing evidence and exact comparisons. Adopt an **aligned relation ledger** as the characteristic object. Each horizontal row is one observed source–target edge. The source is anchored once in the left pane; target rows align to a fixed stage rail. Status text and gate cells communicate outcomes. Position is row order, never score distance or likelihood of truth.

| Edge/target | RETRIEVAL | FEATURES | SCORING | OWNERSHIP | DECODING | RESOLUTION |
|---|---|---|---|---|---|---|
| Selected target ID | Lane chips/count | Schema; values coverage | Score and threshold-reference marker | Owner/rival/rank | Canonical disposition | Emitted/not emitted |
| Another recorded target | Independent lane evidence | Independent availability | Recorded score | Independent owner result | Recorded reason | Recorded membership |

Visual shorthand uses cobalt selection, teal accepted, amber ownership contention and neutral below-threshold. Crimson is reserved for labelled errors and verification failures. An ordinary rejection is not automatically an error. A single-row score bar, if used, has fixed 0–1 extent and a labelled .640 reference line; ownership and decoder columns remain outside it. Acceptance never follows from bar length or row order.

### 8.2 Contention inset

Selecting ownership opens a compact target-centered relation view only when rival evidence is present. It contains selected source, target and recorded rival source, with each known pair score annotated; winner ID/rank is explicit. No inferred relation between source records. Rival details unavailable? Show “Rival identity/score recorded; full source case not retained” and retain the ledger rather than inventing the source's dossier. A loser has a winner rival; an owner has the runner-up. The diagram title must use the appropriate meaning.

An expanded competitor list is a future recorded-artifact feature using all ownership rows for the target. It cannot be reconstructed from a single rival field or bounded top-candidate snippet. Graph nodes are focusable alternatives to the same selected-pair actions; an equivalent native table is always available. Limit visible relation detail to selected edge plus one rival in Slice 1. No force layout, animated particles, artificial clustering, invented nearest neighbors or dense hairball.

### 8.3 Scope and completeness

The ledger is a presentation of known edges, not a newly computed graph. Indicate `N observed / M declared` when M is known. Nonretrieved truth is a separate Evaluation row headed “Labelled truth absent from candidate graph”; do not draw it as a retrieved edge. If the target record is missing, its ID still supports a truth-pair entry, without a fabricated name, score or rank.

## 9. Failure Atlas

### 9.1 Exact attribution semantics

Use the machine enum `AMBIGUOUS_OR_INSUFFICIENT_EVIDENCE`, with display label “Explicit label/data ambiguity” and the exact enum available. Despite its enum name, incomplete artifacts do not qualify: code raises. Explicit nonempty annotation overrides other gates for an error pair.

| Error | Gate precedence after explicit annotation check |
|---|---|
| False negative | Pair absent → RETRIEVAL; retrieved score < .640 → SCORING; otherwise non-owner → OWNERSHIP; admissible owner not emitted → DECODING |
| False positive | Emitted retrieved pair with score >= .640 → SCORING; otherwise → DECODING |

DECODING can identify inconsistent emission artifacts; baseline has no additional set policy. A test injects such a defect, but no C4 recorded decoding failure is present. Do not use unit-test data as a measured run example. “Accepted false positive” is valid: policy acceptance and labelled correctness are distinct.

### 9.2 Wireframe and interactions

| Top, full width | Context + attribution policy + counts in native stage/error table |
|---|---|
| Filter rail | Stage · FN/FP · retained tag/cohort if available · run/definition · evidence coverage |

| Main 64% | Detail 36% |
|---|---|
| Error-pair table: source, target, type, stage, coverage | Selected error: recorded source, truth set, emitted set, diagnostics |
| Bounded example count separate from aggregate count | Candidate snippet, exact ambiguity annotation when supplied |
| Comparison mode: movement-count table | Open case in Explorer; supporting evidence links |

Counts are **error pairs**, with FN and FP separate. Changing a stage filter shows its aggregate count and how many examples are inspectable. For C4 reference, 21 total errors and only 7 retained Atlas examples; never render seven rows as “all failures.” Bulk artifact attachment can unlock the complete list later. A C3 example with scalar diagnostics is inspectable as attribution-only, not a full C4 Atlas entry.

Case selection is durable through `case` and context query parameters. Clicking “Open in Explorer” carries source, target, run and definition. Nonretrieved target opens an Evaluation focus with an explicit missing candidate message, not an invalid-link error.

Comparison uses retained `comparisons[name].failure_stage_movement`. Rows such as SCORING → NOT_ERROR are transitions over the union of error-pair keys; NOT_ERROR is not a policy stage. Aggregate movement has no per-case membership in compact evidence. Clicking a transition may select the count and its evidence reference, but may not produce guessed members. Bulk paired attribution tables are required to enable case drilldown. No Sankey in Slice 1: a sparse exact count table is clearer.

Preserve zero observed stage counts. Filters for OWNERSHIP/DECODING may legitimately return no C4 entries. Do not backfill them with demonstrations from another run without an explicit context switch.

## 10. Experiments

### 10.1 Catalogue and detail wireframes

| Catalogue full width | Synthetic context · 12 diagnostic definitions · No automatic promotion |
|---|---|
| Main native table | Definition · scorer/retrieval/group change · query count · P/R/F0.5/exact-set · diagnostic status · detail link |
| Bottom reference strip | Population, split, schema and fixed decoder; metrics link to recorded result |

| Detail top, full width | Definition identity · run/platform/role · DIAGNOSTIC ONLY |
|---|---|
| Comparison statement | Challenger minus reference delta, descriptive interval, NO ESTABLISHED WINNER when interval crosses zero |

| Detail main 68% | Right context 32% |
|---|---|
| Tabs: Comparison / Cohorts / Failures / Robustness / Calibration | Exact definition and changed fields; schema/model/retrieval/decoder identities |
| Metric table plus interval plot | Training-only fitting/mining boundary; synthetic limitations |
| Cohort deltas and counts; failure movement counts | Producer, environment and artifact links |

Catalogue order follows `experiment_suite`: reference, logistic, six feature-group ablations, k1, no_reverse, transliterated_name, logistic_seed7. User sorting is allowed, but never names a winner. Store exact machine names; give readable labels alongside them. Distinguish an experiment definition from its manifest execution and calibration/test result.

### 10.2 Comparison policy

Default comparison is selected definition versus reference in the same C4 execution/platform and role=test. Only that direction has retained paired comparison evidence. Do not offer arbitrary logistic-versus-k1 inferential intervals. Aggregate metrics may be viewed side-by-side across compatible contexts, but paired claims require actually aligned per-query evidence and a recorded computation; disable absent comparisons with a precise reason.

Validate dataset/split/schema/decoder identity before calling results comparable. Retrieval/model identity may differ as the intervention; make those differences visible. Do not compare C3 F0.5 0.614583 against C4 F0.5 0.842105 as a performance gain: their populations differ.

For logistic display: reference 0.842105, comparison 0.864662, delta +0.022556, descriptive interval [-0.015038, +0.067669], `DIAGNOSTIC_ONLY`, “Interval includes zero; no scorer winner established on this fixture.” No “significant,” trophy, “promoted” or statistically equivalent claim. Even an interval excluding zero would remain diagnostic under existing promotion policy. The interval resamples synthetic queries sharing targets/templates and is not external generalization evidence.

Feature ablations zero existing group columns at train and score and retrain; they preserve all 59 positions. They are not isolated causal interventions: retained graph/cross-script signals overlap removed information. Retrieval variants have distinct configuration identities. The transliterated-name challenger keeps original candidate provenance on overlap and marks rescued rows with transformed-name evidence; `origin_by_pair` is compacted out, so per-pair origin is G for committed C4 summaries even where aggregate rescue information exists.

### 10.3 Supporting tabs

Cohorts: table with recorded query count, metric or delta, and population definition; comparisons use reference memberships as retained. Do not total overlapping cohort counts. Tag conventions can combine missing and empty country/name values; show the documented recorded cohort label and do not infer a lossless raw-data split from it.

Robustness: perturbation, changed original queries, denominator 133, change rate, candidate/quality changes, changed-ID links with coverage. Competition adds a query to its full quality report; its original-query change denominator remains 133. Case 0/133 is an observation, not universal invariance. Changed IDs alone cannot support before/after target-set inspection; observations.json is L. Row permutation and repeat flags are specific executed checks, not a general stability badge on every case.

Calibration: retrieved-pair count, Brier/log loss/ECE/AUROC/AUPRC and recorded bins; undefined metrics remain null with reason. No fitted slope/intercept, transform or tuned threshold. A reliability plot is optional later, with counts and empty bins visible. It cannot represent end-to-end resolution calibration.

Risk/structure study: metric table only in Slice 1. Committed compact evidence retains aggregate diagnostic comparisons, but removes risk-coverage curves and raw confidence rows. Do not draw those curves from AUROC or risk-at-90 alone. No “stable/unstable” classifier or confidence score added to cases.

## 11. Scale / Profiler

Title: **Measured experimental workloads**. Context states “Synthetic workloads; recorded execution.” No auto-refresh, cluster map or live-health header.

| Top, full width | Platform · workload size · stage · repetitions/warmups · measurement limitation |
|---|---|
| Main plot region | Median pipeline seconds versus available query counts, min–max ranges; table toggle |
| Main table | Queries · targets · candidates · pipeline median/range · maximum sampled process RSS · retained bytes |
| Selected workload | Stage timing table; repeated resolution fingerprints; method/configuration/environment |
| Evidence footer | Scale manifest and observations.parquet occurrence; original bytes availability |

Current sizes are 128, 512 and 2048 queries; one warmup and three measured repetitions per size. Windows pipeline medians are 1.980, 10.413, 73.578 seconds; ubuntu_wsl medians are 1.475, 8.037, 75.444 seconds. Candidate counts are 2931, 11338 and 44559. Display exact retained values on demand. Do not interpolate to larger volumes, fit a complexity law or claim production capacity.

Default plot shows one platform. A side-by-side platform table is allowed with the visible note: same physical host, overlapping suites, uncontrolled observations; no speed winner. Pipeline timers include sampler bookkeeping but exclude imports, fixture generation, model loading, GC and serialization. C3 operational timers have different boundaries and cannot be overlaid as equivalent profiler values.

RSS is process RSS sampled every 10ms plus stage boundaries, includes dependencies/allocator state and can miss spikes. It is neither stage allocation nor an OS peak. Stage RSS values must not be stacked or summed. Stage medians also do not necessarily sum to pipeline median. Default stage cost presentation is a seconds table; later raw repetition plots can display each measured stage and bookkeeping residual only when accurately computed from matching repetitions.

Workload throughput fields, if exposed in advanced detail, are explicitly measured queries/candidates divided by elapsed workload time. They are not production request QPS. Retained-stage byte count is a scoped output total, not database capacity or all-run disk usage. Raw repetition rows are unavailable in the compact checkout; min/median/max summary is sufficient for Slice 1 and must not imply three visible raw points.

## 12. Evidence / Provenance

### 12.1 Evidence browser and detail wireframes

| Browser top | Run/platform · stage/schema · byte availability · verification filters |
|---|---|
| Full-width table | Occurrence/path · stage · schema · physical hash · bytes · producer · coverage |
| Scope footer | Loaded manifests and declared parent coverage; external identities remain unresolved |

| Detail top | Occurrence ID/path · exact physical hash · expected size · producer |
|---|---|
| Identity region | Declared lineage/config/schema/class, separately labelled logical identities |
| Main 65% | Right 35% |
| Parents / Artifact preview / Producing observations tabs | Verification ledger: current check versus recorded retention report |
| Optional one-hop lineage graph; table equivalent | Environment and Git state; return to initiating case/experiment |
| Children table derived from loaded manifests only | Missing external identities and unsupported preview explanation |

The manifest's artifact-map key is its relative path/occurrence location; physical SHA-256 is content identity. Different producers can yield identical bytes. Preserve separate occurrence records and merge only content nodes in the optional DAG. A configuration or logical dataset hash may be a parent identity without corresponding file bytes; render it as an external/unresolved identity, not a fabricated dataset artifact.

Build edges exclusively from `lineage.parent_sha256`; do not draw the entire conceptual pipeline as if every adjacency were a declared parent edge. Children are a reverse lookup over loaded lineage, and must be captioned “Children in loaded evidence” rather than exhaustive global children. Environment is inherited from the producing manifest, not a property of a byte hash. Do not expose deleted or unavailable provenance.

### 12.2 Verification semantics

| Status | Permitted meaning |
|---|---|
| Metadata valid | Current schema/config/lineage validation succeeded on available manifest data |
| Recorded retention verified | Bundle states original outputs passed retention checks; current output bytes are not attached |
| Bytes verified now | Actually loaded original artifact bytes match declared SHA-256 and size; show observation scope |
| Bytes not supplied | Metadata exists, original file is absent; no current physical verification claim |
| Verification failed | Current bytes/schema/identity checks failed; dependent evidence is blocked |
| External identity | Parent digest is known, producing file/definition is unresolved |

Do not use one green “verified” badge for all six. Schema validation and DAG validation alone do not prove original files, model validity or real-world truth. Committed bundle fragment bytes are different from the original files they summarize. Their JSON pointer identifies the fragment; it is not the original artifact hash. Do not hash a compacted reconstructed summary and compare it to an un-compacted original summary hash.

Artifact preview supports available JSON/typed records and bounded plain text only. Parquet/model bytes absent? Offer metadata with a read-gap message. A download action requires actual attached bytes and an appropriate delivery mechanism; a local `outputs/...` path in a manifest is not a working web URL. No in-product “verify original artifacts” action if no bytes are accessible.

## 13. Global search / command navigation

Ctrl+K / Cmd+K opens a labelled dialog. It searches a scoped recorded index and provides navigation commands to the five global sections, copy-current-link and open-current-evidence. No run, train, promote, resolve-new-record or write commands.

Index types: source IDs, target IDs, retained failure-pair handles, experiment names/definition handles and artifact occurrence paths/hashes. Exact ID matches rank before prefix matches; deterministic lexical order within type, grouped by run. Optional substring matching is literal recorded-index matching, never the Concord entity-resolution engine or semantic search. Search state is a navigation convenience; selecting a hit opens a durable route.

Results state “Searching loaded evidence only.” Same ID in C3/C4 must have separate hits with dataset/run/platform. Target hits open a result group of recorded source edges/error pairs, then Explorer; a target alone is not a source case. Metadata-only hits say “Details not retained.” Unknown ID returns “Not found in loaded evidence,” not “Entity does not exist.” Complete target-to-source reverse lookup is G without full stages.

Wireframe: dialog top is search input and scope, center is grouped result list with ID/context/coverage, bottom is keyboard help and indexed-evidence boundary. Use a combobox/listbox interaction with status count announcements, Escape to dismiss and focus return.

## 14. Frontend conceptual domain model

This is a field contract for a future adapter; no TypeScript or frontend code is introduced. Fields listed here are exhaustive for V1 business data. Additional implementation-only layout keys must not become backend facts.

| Object | Fields | Interpretation |
|---|---|---|
| EvidenceContext | runHandle, bundleRef, platform, manifestKey, experimentId, definitionName?, role?, datasetFingerprint, splitFingerprint?, origin, delivery, evidenceClass, producerCommit | Immutable observation scope; UI handles are D |
| ReadEvidence<T> | availability, value?, references[], coverage?, issue? | availability: available / not_retained / not_applicable / malformed / verification_failed; zero is a value, not availability |
| EvidenceReference | contextHandle, artifactOccurrenceHandle?, bundlePath?, jsonPointer?, recordedPhysicalHash? | Points to exact source of a field; absence is explicit |
| Coverage | loadedCount?, declaredCount?, extent, limitation | extent: complete / bounded_example / summary_only / partial; D from known counts |
| SourceEntity | entityId, source, rawName, rawAddress, country, entitySchemaVersion, normalizedName, normalizedAddress, normalizationVersion | Text fields are ReadEvidence<string or null>; null raw text is an available value |
| ResolutionCase | context, sourceId, source, candidates[], candidateCoverage, resolution, capsule, failures[], truthTargets | Joined view; missing collections do not mean empty outcomes |
| CandidateEvidence | pairKey, targetId, targetSource, target, retrieval, features, score, ownership, disposition, emitted | Read-only independent stages; target metadata may be absent |
| RetrievalProvenance | viewMask, laneEvidence[], country, retrievalIdentity, config, fitEvidence, warnings, representationOrigin | Lane evidence: lane, rank, similarity; origin may be G |
| FeatureEvidence | schemaVersion, schemaSha256, orderedDefinitions[], values, effectiveValues, removedIndices | Definitions: index, name, definition, definitionVersion; effective inputs may be D |
| ScoreEvidence | score, modelSha256, modelVersion, scorerKind | Numeric probability and model identity; kind from run definition/config |
| OwnershipEvidence | isOwner, ownerRank, rivalSourceId, rivalScore, rivalMargin, policyVersion | Null singleton rival remains available-null |
| ResolutionDecision | sourceId, acceptedTargets, decisionType, decoderVersion | Actual emitted set, never top-score approximation |
| CandidateDisposition | score, isOwner, threshold, thresholdMargin, accepted, rejectionReason, decoderVersion | NONE/BELOW_THRESHOLD/LOST_OWNERSHIP; reserved SET_POLICY not displayed as observed |
| ResolutionCapsule | candidateCount, topCandidateScore, minAcceptedLaneCount, allAcceptedHaveAlternateLane, minOwnershipMargin, minThresholdMargin, ambiguityRatio, identityFields | Identity fields use exact backend names mapped in Section 15 |
| FailureCase | context, sourceId, targetId, errorType, failureStage, policyVersion, tags, diagnostics, source, truthTargets, acceptedTargets, candidateCount, candidateExamples, atlasIdentity | C3 attribution-only and C4 Atlas coverage differ |
| ExperimentRun | context, definition, definitionSha256, manifestDisposition, promotion, resultByRole, comparisonToReference, robustness, repeatChecks, seedSensitivity | Definition fields: name/scorer/removedGroup/retrieval/seed/schemaVersion |
| EvaluationResult | population, queryCount, metrics, linkCounts, calibration, cohorts, failures, candidateCount, identities | Metrics and reports mapped without adding absent per-query rows |
| ScaleWorkload | context, queryCount, targetCount, candidateCount, datasetFingerprint, resolutionFingerprint, repeatFingerprints, stageSummaries, retainedStageBytes, configuration, environment, rawObservations | Raw observations G in committed-only adapter |
| ScaleObservation | queryCount, targetCount, candidateCount, repetition, stage, wallSeconds, sampledPeakRssBytes, startRssBytes, samples | Exact local typed contract |
| EvidenceNode | occurrenceHandle, context, relativePath, physicalHash, expectedBytes, lineage, environment, verification, parents, loadedChildren, preview | Occurrence and content identity are separate |
| SearchHit | type, key, context, label, coverage, destination | All D from indexed observed objects; no external enrichment |

`metrics`, `diagnostics`, `configuration`, `environment`, `lineage` and `identityFields` are versioned maps of actual source keys, not arbitrary “AI metadata.” Unknown fields are preserved for raw inspection but not interpreted. Semantic display schemas are enumerated in Section 15.

## 15. Mapping domain objects to actual backend/evidence

For compact selectors below, `A`, `B`, `C` mean the corresponding PASS_*_RUNS.json files; `P` means `.platforms[platform]`; `R` means `C.P.public_results`; `M` means a selected manifest; `E` means a selected C4 retained Atlas example. Paths are relative to repository root. All copied fields retain references. A “G” mapping must render unavailable unless independently supplied validated L bytes.

| Frontend fields | Exact mapping / derivation | Availability |
|---|---|---|
| Context bundleRef/platform/manifestKey | Bundle file and keys in `.platforms`/`.manifests`; SHA of loaded bundle is D, not an embedded producer fact | C/D |
| experimentId/manifestDisposition/producerCommit | `M.experiment_id`, `.disposition`, `.git.commit_sha`; dirty from `.git.dirty` | C |
| datasetFingerprint/splitFingerprint/origin/class | `M.provenance.dataset_fingerprint`, `.split_fingerprint`, `.dataset_track`; `M.evidence.class` | C |
| definitionName/role | C4 `R.experiments[name].roles[role]`; C3 summary keys calibration/test | C/D |
| runHandle/occurrenceHandle/search destinations | Composite scope handles, Section 19 | D; new read index G |
| Source/target entity fields | `EntityRecord`: entity_id, source, business_name, business_address, country, schema_version; C4 E.source_json and E.candidate_evidence_json[].target | C for examples, L for all entities; C3 raw records G from compact summary |
| normalized fields/version | `NormalizedEntity` and normalized.parquet; source normalizer is code, not recorded bytes | L/G; schema can be inspected C |
| pairKey/targetId/targetSource | RetrievalCandidate.s1_id/target_id/target_source, scoped to context; selected snippets agree across stages | C selected; L complete |
| viewMask/laneEvidence/country | RetrievalCandidate.retrieval_view_mask/lane_evidence/country; `lane, rank, similarity` | C snippets; L candidates.parquet |
| retrievalIdentity | Capsule retrieval_config_sha256 or C4 role result retrieval_sha256; config identity may include challenger adapter | C where retained |
| config/fitEvidence/warnings | RetrievalConfig fields and FitEvidence fields in retrieval-definition JSON / C2 reports/manifests; C4 graph definition outputs | C only where embedded, otherwise L/G; do not assume capsule includes them |
| representationOrigin | C4 retrieval_definition.json `.origin.origin_by_pair`; removed by compact(); raw representation adapter described in code | L/G per pair; no fabricated sixth mask bit |
| feature schema/version/definitions | `features/reference.py:REFERENCE_SCHEMA`; FeatureDefinition name/definition/definition_version; schema SHA checked against row/capsule | C contract, L serialized feature_schema; no casual alias of physical hash to schema SHA |
| values | FeatureRow.values or feature columns ordered by c3_storage.DEFINITIONS['features'] | L/G; no values in C4 candidate snippets |
| removedIndices/effectiveValues | ExperimentDefinition.mask / GROUPS; zero-mask of validated base values | C/D if values exist; otherwise G |
| score/model identity/version | ScoredCandidate.score/model_sha256/model_version; C4 snippet `.score`; C3 top_rejected disposition carries score and capsule model_sha256 | C selected, L full; C3 absent modelVersion remains unavailable unless supported by manifest |
| scorerKind | C4 definition.scorer; C3 validated fit stage/config | C/D where context explicit |
| ownership fields | OwnershipResult.is_owner/owner_rank/rival_s1_id/rival_score/rival_margin/ownership_policy_version | C selected / L full |
| disposition fields | CandidateDisposition.score/is_owner/threshold/threshold_margin/accepted/rejection_reason/decoder_version | C selected / L full |
| final sourceId/acceptedTargets/type/version | ResolutionDecision.s1_id/accepted_targets/decision_type/decoder_version; C3 capsule provides first three; C4 E.accepted_targets derives type by size | C examples/D; decoder version only with supported config/record |
| emitted | Membership in actual complete accepted_targets when present | D; unavailable when set not supplied |
| Capsule diagnostics | ResolutionEvidenceRecord exact snake_case fields listed in Section 14 and c3_contracts.py | C B.P.summaries['summary.json'].evidence_example.evidence; L C4 capsules.json |
| Capsule identityFields | dataset_fingerprint, split_fingerprint, retrieval_config_sha256, feature_schema_sha256, model_sha256, decoder_config_sha256, code_commit | C B example; L all capsules |
| Failure source/target/type/stage/tags/diagnostics/policy | FailureAttribution.s1_id/target_id/error_type/failure_stage/tags/diagnostics/attribution_policy_version; C4 role result `.failures.examples`; B summary `.failures[role].examples` | C bounded, L full |
| Atlas source/sets/count/examples/identity | E.source_json/truth_targets/accepted_targets/candidate_count/candidate_evidence_json/run_identity_sha256 | C 7 reference examples/platform; L all Atlas |
| Failure aggregate count/entry coverage | C.P.failure_atlas.counts/entry_count/examples; result.failures.counts | C; examples length D; no complete listing inferred |
| definition/definitionSha256 | C.P.manifests.public.pipeline_configuration.definitions[]; R.experiments[name].definition_sha256 | C |
| resultByRole/identities | R.experiments[name].roles[role]; population, dataset_fingerprint, split_fingerprint, retrieval_sha256, feature_schema_sha256, model_sha256, decoder_sha256, score_fingerprint, resolution_fingerprint | C |
| metrics/linkCounts | role result.quality: macro_precision, macro_recall, macro_f05, exact_set_accuracy, query_count, tp, fp, fn, accepted_link_count, population; B summary.quality[role] | C; per_query explicitly G |
| calibration | role result.calibration or B summary.calibration[role]: pair_count, bins(lower/upper/count/mean_score/positive_fraction), auroc, auprc, brier_score, log_loss, ece, score_distributions, slope/intercept null | C; no added calibration fit |
| cohorts/failures/candidateCount | role result.cohorts/failures/candidate_count; C3 corresponding summary/report if present | C |
| comparisonToReference | R.comparisons[name]: macro_f05(delta,ci95,query_count,bootstrap_repetitions,seed,meaning), absolute_metric_deltas, cohort_f05_delta_on_reference_membership, failure_stage_movement, promotion, resources, retrieval | C; only actual keys |
| robustness | R.robustness[name]: evaluated_original_query_count, changed_count, change_rate, changed_queries, quality, cohorts, profile, dataset_fingerprint, candidate_count, calibration, failures, retrieval | C; before/after sets L/G |
| repeatChecks/seedSensitivity | R.repeat_equal/row_order_equal; C.P.logistic_seed_sensitivity(seeds,query_count,changed_count,decision_change_rate) | C; no per-case stability boolean |
| promotion | M.promotion or comparison.promotion=`DIAGNOSTIC_ONLY`; no winner derived from max metric | C |
| ScaleWorkload counts/identities | C.P.scale_results.workloads[size]: query_count,target_count,candidate_count,dataset_fingerprint,resolution_fingerprint,repeat_resolution_fingerprints,retained_stage_bytes | C |
| stageSummaries | workload.stages[stage]: median_seconds,range_seconds,maximum_sampled_rss_bytes,median_queries_per_second,median_candidates_per_second | C; raw repetition points G |
| scale config/environment | C.P.scale_results.configuration/environment; fields warmups_per_size,repetitions,sizes,workers,model_threads,hardware,memory_method,timing_scope,recipe,model_fingerprint,parent_model_artifact; environment os/python/cpu/packages/available_ram_bytes/implementation_source_sha256 | C; retain observed units |
| ScaleObservation fields | `research/definitions.py:ScaleObservation`, `research/scale.py:SCALE_SCHEMA`; observations.parquet snake_case fields | L/G in compact mode |
| EvidenceNode path/hash/bytes/lineage | `M.artifacts[relativePath]`: sha256,bytes,lineage(artifact_sha256,parent_sha256,configuration_sha256,code_commit,schema_version,stage,evidence_class) | C metadata; file payload L/G |
| Evidence environment/parents/children | M.operational.environment; exact parent_sha256; reverse lookup of loaded lineage parents | C/D; external parent expansion G |
| verification/preview | D current parse/schema/bytes checks; recorded counts/logs in bundles separate; preview only available payload | D; original-byte checking G if absent |
| coverage/availability/reference/issue | D from supplied content/counts, schema checks and explicit absence; issue uses Section 20 codes | D presentation; no backend field asserted |

Model fingerprint and artifact physical hash can differ. C4 numerical model identity is emitted by ResearchScorer.fingerprint; the model.json file's physical hash is a manifest artifact hash. Never use them interchangeably. Likewise a logical score fingerprint is not scores.parquet's byte hash.

## 16. BACKEND READ GAPS

These gaps are observed from code, retained bytes and CLI boundaries. No API or exporter is implemented in this task. “Backend read gap” includes output-delivery and indexing gaps even where the computation already exists.

| ID | Gap | Affected interaction | Slice 1 disposition / later requirement |
|---|---|---|---|
| G01 | No HTTP inspection/read service | Every remote case/feature/artifact lookup | Recorded adapter; future read service separate decision |
| G02 | No complete public case/candidate index | Arbitrary source and target search | Index supplied examples only; completeness label |
| G03 | Full candidate, normalized, feature, score, owner/disposition/decision Parquet absent from Git | Complete case reconstruction and feature values | Explicit missing sections; later consume verified local outputs |
| G04 | C3 explain returns capsule + five rejects, not entities/features/all candidates | “Full trace” from explain JSON alone | Mark bounded/partial; do not call it complete |
| G05 | C4 reference Atlas retains 7 examples of 21 errors | Complete Failure Atlas list | Counts plus retained-example browser; full atlas.parquet needed |
| G06 | Compaction removes per_query and transition membership | Metric drilldown; error movement case list | Aggregate comparison only; paired typed rows needed |
| G07 | Compaction removes origin_by_pair | Per-candidate transliteration challenger representation | Origin unknown; local retrieval_definition.json required |
| G08 | Compact perturbations retain changed IDs, not before/after sets | Robustness case diff | IDs with coverage; local observations and stages needed |
| G09 | Raw scale observations absent | Repetition scatter/distribution and precise stage contribution | Median/range table/plot only; observations.parquet needed |
| G10 | No browser-resolvable artifact bytes/query endpoint | Current physical verification, preview/download | Declared metadata versus recorded check; attachment/export transport later |
| G11 | External parent digests may have no loaded producer | Complete lineage expansion | Unresolved identity nodes; never fabricated ancestry |
| G12 | No run registry/lifecycle/read stream | Live local run, refresh, progress, scheduling | Future only; no working live selector |
| G13 | No feature contributions/counterfactual explanations | “Why this score?” causal account | Values/definitions only; exclude SHAP/LLM narrative |
| G14 | No actual frontend-normalized adapter/export schema | Convenient stable UI reads from multiple file layouts | Proposed recorded mapping/index layer; no endpoints assumed |
| G15 | C3 compact example lacks raw source/target records | Complete source pane for high-score tie demo | ID with unavailable raw fields; validated fixture/run export needed later |
| G16 | No complete target competitor view from a rival snippet | All rival inspection | One recorded rival only; full ownership/score tables required |

Capability presence is per context and per resource, not a global boolean inferred from one successful example. Local bulk files solve data availability; they do not automatically solve browser access or stable query interfaces. Fixture code alone can reproduce invented records, but a generated record is not recorded-run evidence until its identities are checked against the chosen run. Do not solve G03 by re-training silently during frontend build.

## 17. RecordedEvidenceAdapter strategy

The adapter is the only layer interpreting raw bundle/output layouts. Views depend on Section 14 objects and structured availability, not raw `platforms.windows.public_results` paths. There is no server requirement for the committed-evidence variant.

Proposed read operations: listContexts, listCases, readCase, readCandidate, listFailures/readFailure, listExperiments/readExperiment, readScale, listArtifacts/readArtifact, search. These are future adapter method contracts, not current Concord endpoints. Each returns a domain result or a Section 20 issue plus coverage/references. Pagination/searching within a bounded example set never suggests complete backend coverage.

Committed-evidence ingestion:

1. Load only explicitly selected current bundles; compute a delivery-byte identity and validate version/shape. Validate embedded manifests using matching semantics, including configuration fingerprint and declared DAG. Exact manifest/schema checks should be reused through a later local conversion step or implemented equivalently; browser parsing alone is not physical verification.
2. Create independent contexts for pass/platform/manifest/definition/role. Keep producing commit distinct from repository HEAD. Build a finite index of retained examples, metrics and artifact occurrences.
3. Join snippets by context plus source/target identity. C3 evidence_example and failures can enrich only the same declared population. C4 attribution examples may join Atlas examples only after identity/context agreement. Same string IDs across C3/C4 are never join keys by themselves.
4. Preserve literal scalar values, nulls, schema order and canonical reasons. Carry exact bundle pointers for every presented evidence group. Do not substitute manifest metrics for missing case outcomes.
5. Return bounded/summary coverage by default where full stage bytes are absent. Cache by loaded content identity plus complete context; invalidate on bundle-byte change.

Optional later local recorded-artifact ingestion consumes **already produced** validated output directories, checks original SHA/size/path containment and stage schemas, joins all stages, and provides values/full cases. It remains recorded mode, not live mode. A later reviewable export may package bounded typed JSON suitable for browser consumption, with source references and coverage. Do not stage full models/Parquet by default or rewrite current bundles just to simplify UI access.

Adapters reject contradictory duplicate records rather than selecting the prettier value. They must not recompute model predictions, ownership or attribution to fill missing evidence. Deterministic consistency checks are permitted and labelled checks; missing proof stays missing. Unavailable data is typed, not hidden behind network-looking loaders.

## 18. Future live adapter boundary

LiveConcordAdapter is an architectural reservation only. It may implement the same read operations once an actual local run registry/read service exists. It must identify immutable snapshots, complete global candidate populations, producing model/config/schema and artifact consistency before showing decision evidence.

A mutable RUNNING record cannot masquerade as a COMPLETED case. Loading partial live outputs must be explicit, with consistent snapshot boundaries or unavailable states. Run execution, training, cancellation, writes, authentication and job control are outside this product specification's read-only V1. Do not add mock live endpoints, synthetic pollers or demo activity feeds. Shared domain objects are the compatibility boundary; raw file layouts and prospective API URLs are not.

## 19. URL / deep-link and state model

Every analytic link identifies context. Opaque IDs are percent-encoded as single URL segments/values; never lowercase, trim or treat them as filenames. Stable handles are URL-safe base64 encodings of canonical composite identity data, not claimed backend UUIDs.

| Handle | Canonical inputs |
|---|---|
| run | bundle path + loaded bundle physical SHA + platform + manifest key |
| experiment | run handle + definition name |
| artifact | run handle + manifest-relative artifact path + declared physical SHA |
| case | run + definition/role + source ID + target ID + error type for failure selection |

Embedding bundle-byte identity pins a deep link to that recorded version. A later bundle version cannot silently serve a different case under the same handle. The adapter may identify a replaced bundle and offer an explicit context-switch link, not an automatic redirect to newer measurements.

| State | URL representation |
|---|---|
| Source case | `/explorer/{source}?run={handle}&definition=reference&role=test` |
| Selected candidate | Add `candidate={target}` |
| Evidence detail tab / stage focus | `tab=retrieval|features|raw|provenance`, `focus=retrieval|features|scoring|ownership|decoding|resolution|evaluation` |
| Candidate sort/filter/page | `sort=score_desc|target_asc`, `disposition=...`, `lane=...`, `page=...` |
| Atlas stage/type/case | `/failures?run=...&definition=...&role=test&stage=OWNERSHIP&type=FALSE_NEGATIVE&case={handle}` |
| Recorded reference comparison | `/experiments/{handle}?role=test&tab=comparison` |
| Atlas movement | Add `compare={definition}&movement={encoded transition}`; count-only if membership absent |
| Artifact occurrence | `/evidence/{handle}`; content hash shown in body |
| Evidence filters | `/evidence?run=...&stage=...&availability=...` |
| Scale observation | `/scale?run=...&platform=windows&size=2048&stage=pipeline` |

Example analytic paths use real recorded IDs but run handles are adapter-resolved placeholders here: `/explorer/test-own-a?run={C-windows-public}&definition=reference&role=test&candidate=test-own-target`; `/explorer/test-amb-z?run={B-windows-resolve-test}&role=test&candidate=test-amb-target`. These refer to different populations and must show that difference.

With missing `run`, display a context chooser or the only unambiguous available context; when resolved, canonicalize the URL. Never guess between C3/C4 solely from source ID. Unknown parameter values produce an inline recoverable issue, retaining valid context. Back/forward restores selection, tabs and filters. Use push history for explicit case/candidate/context navigation and tab/filter actions; replace for canonical defaults/debounced filter text. Pane sizes, scroll offsets, tooltip state and focus position can remain local preferences. Critical analysis state cannot.

Selected candidate remains selected when a filter excludes it; show “Selected target hidden by filter” with Clear filters. Do not silently select a different candidate. Invalid candidate versus deliberately nonretrieved truth use different states. Links from evidence carry a validated same-product `returnTo`; avoid arbitrary external redirects.

## 20. Empty, loading, degraded and error states

| Code/state | Required UI and recovery |
|---|---|
| LOADING | Stable workbench skeleton with aria-busy; no placeholder scores, graph edges or success statuses; preserve prior context visibly during navigation |
| SOURCE_NOT_INDEXED | “Source ID not found in loaded evidence”; show scope and case catalogue/search; do not infer global nonexistence |
| SOURCE_RECORD_NOT_RETAINED | Keep source ID/case evidence; raw field panel states missing record; recorded IDs remain useful |
| NO_CANDIDATES | Only when candidate_count=0 is recorded: empty ledger, no score, valid empty result if recorded; labels may show retrieval FN separately |
| NO_ACCEPTED_TARGETS | Valid zero_match; retain rejected candidates, threshold/ownership gates and coverage; do not call this an execution error |
| MISSING_EVIDENCE | Name stage/artifact and pointer; show existing stages; no invented success/failure |
| INVALID_CANDIDATE_LINK | Known case but selected target not in supplied candidates: differentiate omitted bounded evidence from proven nonmember; keep ID in warning and allow explicit clear selection |
| NONRETRIEVED_TRUTH | Known error/label pair absent from graph; show Evaluation row, no candidate score/features/ownership |
| VERIFICATION_FAILED | Expected/observed hash or size, artifact and check scope; block dependent evidence; offer other validated resources; never label this a labelled model failure |
| UNSUPPORTED_EVIDENCE_TYPE | Keep manifest metadata, show unsupported version/type; raw bounded text only if safely readable; no silent schema coercion |
| FIXTURE_ONLY | Persistent synthetic ribbon and limitations; no fake production toggle |
| BACKEND_READ_GAP | Name Gxx and required recorded artifact/access; no retry loop for a capability that does not exist |
| EXPERIMENT_UNAVAILABLE | Definition or context absent; show available catalogue; keep missing handle in explanation |
| SCALE_UNAVAILABLE | Workload/platform/stage absent; show valid combinations; never interpolate |
| PARTIAL_EVIDENCE | Loaded/declared counts, missing stages and limitations; summary-backed results remain visible with their coverage |
| MALFORMED_ARTIFACT | Version/path/field/type problem, bounded technical detail; isolate failed artifact and dependencies; no acceptance inference |
| INCONSISTENT_STAGES | Score/owner/disposition/set or identity disagreement; quarantine joined decision and show references; never repair source evidence in UI |
| UNDEFINED_METRIC | “Undefined” plus existing reason/population; null never rendered as 0 or 100% |
| EMPTY_FILTER | Zero matches within known loaded rows; counts/scope retained; Clear filters |
| INVALID_CONTEXT_OR_VERSION | No automatic fallback to a different recorded run; choose explicitly from available contexts |

Transport failures may offer retry; permanent missing-capability states offer navigation or evidence requirements. No exception text dumps credentials or treats local producer paths as downloadable URLs. Errors are selectable, screen-reader announced and technically specific. An isolated malformed artifact does not require discarding unrelated validated evidence.

## 21. Responsive behavior

| Viewport | Exact degradation |
|---|---|
| Large desktop >=1440px | Section 7 three-pane layout; lower detail spans center/right; panes have independently labelled scroll regions |
| Laptop 1100–1439px | Source becomes a 56px full-width collapsed context strip with expandable inline details; body is candidate pane min 500px plus 320px trace; lower details full width below both |
| Tablet 768–1099px | Two modes under persistent source/result/context header: Candidates and Selected evidence; selected evidence contains trace and details vertically; URL selection persists across modes; source expansion is inline |
| Small screen <768px | One-column case dossier: compact context, source/result summary, native candidate list with target/score/disposition, then selected trace/details; explicit Back to candidates returns focus; horizontal scrolling only inside labelled wide tables |

On laptop, expanding source context increases header height rather than overlaying candidates. On tablet, selecting a candidate may activate Selected evidence only through explicit Inspect action; ordinary row focus does not cause disorienting navigation. On small screens stage rail becomes an ordered labelled stage list. Graph inset defaults to its table alternative. No three panes squeezed into narrow columns, essential tooltip-only values or claim of equal mobile productivity.

Other surfaces use the same rule: filters wrap, detail side regions stack below main tables, table columns stay available through labelled horizontal overflow or explicit column disclosure. Context, synthetic origin, coverage, selected source/target, final set and canonical disposition remain visible at every breakpoint. At 200% zoom behave by effective CSS width, not device classification.

## 22. Accessibility

Target WCAG 2.2 AA in implementation; this specification supplies behavior, not an existing compliance claim.

Use semantic landmarks, a skip-to-workbench link and descriptive region headings. Candidate data is a native table with caption, column headers, row headers and a real Select candidate button in each row. Tab traverses actionable controls; optional Up/Down navigation between row selection controls, Home/End for visible first/last, Enter/Space to select. Do not hijack global arrow keys. Selection is aria-current/explicit selected text on the control, not invalid row semantics. Focus stays at the initiating control until explicit Inspect details.

Tabs follow roving focus and standard arrow/Home/End behavior. Pane splitters are keyboard-operable labelled separators with current/min/max size, or fixed layouts if that cannot be delivered accessibly. Closing a drawer/dialog returns focus to its opener; route changes focus the main heading. Announce candidate selection concisely: target ID, canonical disposition, evidence coverage. Do not read all 59 features on every selection.

Graphs have a complete native table alternative with identical facts/actions, not a screenshot alt string alone. Every status has visible text plus optional shape/icon: accepted check, contention rival marker, labelled error cross, unknown dash with label. Color is supplementary. Loading announces busy; validation/error changes use restrained live regions without repeatedly rereading tables.

Normal text contrast >=4.5:1, large text >=3:1, controls/focus/meaningful graphic edges >=3:1. Focus uses a 2px cobalt outline plus offset; selected rows also use a structural left rule/text marker. Provide 24px minimum targets and prefer 32px controls. Dense rows are at least 36px with 14px body text, tabular numeric figures and comfortable line height. Do not shrink evidence into 10px text. Hash truncation includes Copy full value and accessible full text; IDs wrap without changing bytes.

Tooltips are supplementary, focus/hover accessible, dismissible with Escape and persistent while inspected; they never contain the only threshold, rejection reason, provenance label or error explanation. Avoid hover-only row actions. Respect reduced motion; no ambient animation. Virtualization, if later necessary, must preserve row count/index semantics and keyboard access; Slice 1's bounded data does not require it.

## 23. Complete visual system

Light, editorial instrument styling distinguishes Concord from Relay's dark control-board direction. One integrated workspace, ruled tables, compact context strips and strong selected evidence create density without a card collage.

| Token | Value | Use |
|---|---|---|
| Canvas | #F6F6F3 | Warm neutral page background |
| Surface | #FFFFFF | Workbench and detail regions |
| Primary ink | #15171A | Main text |
| Secondary ink | #5B616B | Supporting labels; chosen darker than initial #6B7280 |
| Hairline | #D8DADD | Decorative dividers only |
| Control boundary | #7A808A | Meaningful input/control borders |
| Cobalt | #2446B8 | Selection, links, learned-score emphasis |
| Selection tint | #EDF1FF | Selected row, always with rule/text marker |
| Teal | #006B60 | Decoder acceptance |
| Amber | #855000 | Contention and caution text |
| Crimson | #A51D35 | Labelled errors/verification failures |
| Violet | #6240A3 | Experiment and provenance identities |
| Teal/amber/crimson/violet tints | #EAF6F2 / #FFF4DE / #FBECEF / #F3EEFA | Small labelled backgrounds; verify text contrast against actual combinations |

Implementation must measure actual contrast and adjust a token if necessary without changing its semantic role. Pale hairlines cannot be the sole meaningful focus/control boundary. Cobalt selection is distinct from acceptance; a selected false positive retains its error label.

Typography: system sans-serif stack with tabular numerals for data; optional locally available editorial sans only if consistent. Use 20px/28px route heading, 16px/24px section heading, 14px/20px body/table, 12px/18px captions. Monospace system stack only for IDs, hashes, versions and raw machine fields. Do not require network font loading. Source names can use 16px medium weight; machine IDs remain visually subordinate to the decision statement without disappearing.

Spacing follows 4/8/12/16/24px. Borders 1px; small control radius 4px and outer workbench radius at most 6px. No pill overload: lane chips are compact rectangular tags with full readable legend. Icons are simple, single-weight and labelled. Shell buttons 32px high; case actions 32px; candidate rows 36–44px with detail expansion as needed. Numeric columns right-aligned; signed margins explicitly use +/−. Metric precision six decimals by default, threshold three, resource seconds three, RSS MiB two; raw exact values remain accessible. Counts use separators, byte units distinguish bytes/MiB and never overwrite retained units.

Motion: immediate selection feedback, at most 120ms opacity/disclosure transition, disabled under reduced motion. No glass, gradients, neon, terminal wallpaper, decorative sparklines, oversized headlines, fake avatars/logos or live activity animations.

## 24. Visualization rationale and gates

No visualization is approved without these three answers and the availability gate. Native tables are the default precise representation.

| Visualization | Question answered | Required data | Why better than a table / gate |
|---|---|---|---|
| Aligned candidate relation ledger | How does each edge pass independently through the pipeline? | Candidate stages, selected pair and coverage | Fixed visual alignment exposes gate separation while preserving exact table semantics; approved defining object |
| Selected score reference bar | Is this score above .640? | Exact score/threshold from same context | One fixed reference marker conveys signed distance rapidly; redundant numeric label required; optional |
| Selected-target contention inset | Which recorded rival owns this target? | Ownership/rival fields and known pair relation | Small topology highlights two sources sharing one target; never all competitors; table default when data/accessibility inadequate |
| Paired interval plot | Does the recorded descriptive delta interval include zero? | delta/ci95/query count/bootstrap metadata | Zero reference and interval reveal uncertainty better than isolated point estimates; approved with exact numeric table |
| Scale median/range plot | How does measured pipeline time vary across these workload sizes? | Same-platform size/median/range summaries | Slope and nonlinearity across measured points are easier to see; no extrapolation; approved |
| One-hop lineage DAG | Which declared parents support this artifact occurrence? | Manifest lineage plus loaded occurrences/external identities | Branching dependencies are clearer than a long list; use only when branching adds value, limit visible nodes and retain table |
| Reliability plot | How do retrieved-pair scores compare to recorded positive fractions? | Bins/counts/means from calibration | Deviations from diagonal are visible; later optional, not empty-bin interpolation or real-world calibration claim |
| Risk-coverage curve | What was risk as cases were retained under a declared order? | Full risk_coverage arrays | Could show coverage tradeoff, but compact bundle removes arrays; blocked in committed Slice 1 |

Use tables for stage/error counts, failure movements, lane evidence/overlap, cohort deltas, ordered features, ablation definitions, raw scale stage summaries and hashes. A fan-out picture of one source and several targets alone adds little over the ledger and is not approved. A conceptual pipeline illustration must be labelled architecture, never recorded artifact lineage.

## 25. Ninety-second demo

This demo is feasible from committed evidence with honest partial coverage. It uses two deliberately different recorded contexts; a later complete-artifact demo may remain within one context only after an actual suitable case is verified. No invented demo scores or fake local replay.

| Time | Action | Engineering fact proved |
|---|---|---|
| 0–15s | Open C4/windows/reference/test `test-own-a`, selected `test-own-target`; show emitted set and synthetic/recorded ribbon | Source-specific resolution with recorded raw source; score 0.931963, accepted, **labelled false positive** |
| 15–30s | Inspect lane evidence and independent owner/decoder sections; open Features coverage label | Retrieval differs from scoring/policy; schema exists but feature values are not retained; no causal fiction |
| 30–50s | Explicitly switch to C3/windows/test `test-amb-z`, target `test-amb-target` | Score 0.999807 clears .640 yet loses to `test-amb-a` at identical score via ID tie-break; final set empty; raw record coverage absent |
| 50–65s | Return to C4 Failure Atlas; select `test-q-0015` / `test-t-0015` | RETRIEVAL FN: zero candidates, missing labelled pair; complete aggregate count versus bounded examples; no score fabricated |
| 65–82s | Open C4 logistic versus reference comparison | Higher point estimate, descriptive interval crossing zero, DIAGNOSTIC ONLY; no established winner |
| 82–90s | Follow result artifact reference into Evidence | Producer/config/schema/parents and declared hash; recorded retention check distinguished from bytes not supplied |

The first accepted case is intentionally also an error; this proves acceptance is policy execution, not identity truth. The C3 tie case's failure attribution is explicit ambiguity, not OWNERSHIP. Its decoder LOST_OWNERSHIP remains independently correct. A separate C3 OWNERSHIP FN (`test-own-z`) can be shown from scalar failure diagnostics, but must not be embellished into a full retained case.

## 26. Frontend Slice 1 recommendation

Build a **read-only recorded-evidence product slice** across the shared shell and all required routes. Primary Explorer uses the seven C4 retained Atlas examples plus the bounded C3 explain example; completeness varies visibly. Do not wait for an inspection API, and do not pretend the compact bundles supply every stage.

Slice 1 includes: scoped case entry, candidate selection and gate ledger, selected trace, lane/raw/provenance details, schema-only feature tab, aggregate/bounded Failure Atlas, twelve experiment catalogue entries with recorded reference comparisons, scale medians/ranges/table, artifact metadata/one-hop lineage table and scoped global search. Required routes have substantive evidence-backed content, not disabled-page placeholders. Small contention diagram and polished plots are secondary to trace correctness.

Slice 1 excludes: arbitrary dataset browsing, complete per-pair features, full competitor expansion, per-transition case members, perturbation before/after set diff, raw repetition plots, risk-coverage curves, original model downloads, current original-byte verification and live execution. Every exclusion has a Gxx mapping and a specific recovery path.

A richer Slice 1 extension may consume validated existing local outputs without changing backend policy. Its prerequisite is actual recorded-artifact access/export with hashes and coverage, approved as a subsequent implementation task. It must never regenerate or alter baseline evidence behind the UI to make screenshots look complete.

## 27. Implementation sequence for a later agent

1. Freeze this product contract and confirm which recorded outputs, if any, will be supplied. Inventory exact bundle versions and contexts; do not assume the Windows output directories exist in an implementation environment.
2. Implement domain availability/reference types and RecordedEvidenceAdapter, validating schemas and context separation. Build inspectable indexes from committed evidence and document actual coverage. This is the first functionality gate, before visual polish.
3. Implement shell, scoped URLs, case catalogue and native candidate ledger. Show a real empty set, a retained accepted false positive, the C3 high-score ownership tie and a no-candidate retrieval miss.
4. Add trace/details, fixed wording templates, evidence navigation and keyboard semantics. Missing feature values stay missing; validate all status distinctions.
5. Add bounded Failure Atlas, experiment catalogue/detail, logistic interval and measured scale views using retained fields. Preserve counts, populations and limitations.
6. Add artifact occurrence browser, declared lineage, external identity handling and verification-status separation; global search indexes only supplied objects.
7. Apply visual system, responsive collapse and meaningful approved charts. Verify deep links, focus, contrast, zoom and malformed/partial evidence behaviors.
8. Only as a separate extension, provide verified local recorded-output ingestion/export; then unlock complete features/cases and raw observations. Live read service and model explanation research remain independent future work.

No instruction in this sequence authorizes implementation during the present documentation task. A later frontend task should use meaningful fixture-backed acceptance checks for stage/context correctness; this documentation commit requires documentation and evidence-mapping review, not a full retraining/reproduction suite.

## 28. Acceptance criteria for product-spec freeze

### 28.1 Specification gate

- Audited baseline is explicit; retained producer differs from HEAD and remains visible.
- Every required route, major surface, selection behavior, layout breakpoint and error state is specified.
- Every proposed domain field maps to code/evidence, deterministic derivation or a named Gxx gap; no data requirement is hidden in a mockup.
- Candidate score, learned ownership, canonical rejection, final set and labelled correctness remain distinct.
- Exact .640 boundary, score/ID tie-break, singleton null rival, below-threshold precedence and explicit ambiguity semantics are specified.
- Full local outputs and compact public coverage are distinguished, including 7/21 C4 Atlas examples and removed per-query/curve/origin fields.
- Same IDs across C3/C4/platforms cannot silently join or replace one another.
- Comparisons remain diagnostic; logistic interval includes zero and establishes no winner.
- Scale scope and RSS limitations preclude production or controlled platform claims.
- Evidence occurrence identity, content hash, logical identity, external parent and physical-verification status are distinct.
- Rendering/accessibility/deep-link rules are concrete enough for an implementation agent to proceed without redefining the product.
- This task changes exactly this specification file and may create one local documentation commit; no push or implementation.

Specification outcome: **PASS for a bounded recorded-evidence design**. Complete-case frontend capability is explicitly gated by G03/G14/G15, not represented as already delivered. This PASS is not frontend acceptance, backend API completion, fresh metric reproduction or production readiness.

### 28.2 Later implementation acceptance examples

| Check | Expected behavior |
|---|---|
| C3 high-score tie | test-amb-z / test-amb-target shows LOST_OWNERSHIP, owner rank 2, zero margin and empty result; explicit ambiguity remains separate attribution |
| C4 same ID | Shows recorded 0.139147 score and BELOW_THRESHOLD, never C3's score |
| C4 accepted false positive | test-own-a emitted target remains accepted and labelled FP; no green correctness claim |
| C4 retrieval miss | test-q-0015 candidate_count=0, truth target absent, score unavailable, RETRIEVAL FN |
| Bounded 63-candidate case | test-q-0006 shows 8 retained examples of 63, not a complete filtered graph |
| Feature evidence absent | Exact 59 schema definitions visible, values unavailable, no fabricated zeros or importances |
| Logistic comparison | Correct delta/interval/query count and DIAGNOSTIC_ONLY; no promotion button/winner |
| Scale | Three known sizes with recorded medians/ranges and process-RSS description; no live traffic |
| Evidence | Original bytes absent produces recorded-check/metadata state, never current bytes-verified |
| URL and keyboard | Copy/reload/back restores context and candidate; focus and graph table alternatives work |

## 29. Explicit forbidden-invention list

Do not introduce competition/team/origin narratives or previous project names absent from current authoritative material. Concord is Adithya Sanjeevi's individual project. Do not reconstruct deleted material.

Do not fabricate production customers, real company records, production QPS, uptime, SLOs, incidents, cluster health, user activity or environmental/business outcomes. Synthetic records and controlled workloads remain explicitly identified.

Do not invent API endpoints, a live run registry, full public stage tables, complete failure lists, unseen raw records, feature values, score causes, SHAP values, attention heatmaps, natural-language AI explanations, counterfactual replays, automatic promotion, tuned thresholds, causal ablation conclusions, general calibration or stability labels.

Do not replace missing data with zero, equate no accepted targets with no candidates, equate acceptance with correctness, infer ownership from per-source ranking, show missing artifacts as ambiguity, change rejection precedence or emit SET_POLICY under the reference decoder.

Do not fabricate C4 OWNERSHIP/DECODING errors because unit tests or C3 have examples. Do not infer omitted per-query metrics, risk curves, transition members, transliteration origin or perturbation target sets from aggregates. Do not cross-join repeated IDs across datasets/runs/platforms.

Do not present recorded retention verification as a current hash check on absent bytes, compact fragment identity as original-file identity, arbitrary parent digests as files or a conceptual pipeline as the declared DAG. Do not overwrite original C1–C4 artifacts or metrics.

Do not write frontend code, scaffold React/Next.js, modify backend source, add APIs, push, or create further commits in this task. The sole permitted deliverable is `docs/CONCORD_RESOLUTION_EXPLORER_PRODUCT_SPEC_V1.md`; the optional single commit message is `docs: define Concord Resolution Explorer product specification`. Stop after this specification and its verification/report.
