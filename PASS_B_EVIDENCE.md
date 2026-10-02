# PASS B EVIDENCE — C3

## Status, branch and checkpoint

**PASS — C3 PUBLIC_PASS.** No C4 work is included.
Starting SHA: `70abb57241b246bec4fcee5b26e672735588e46f`.
Branch: `c3/scoring-resolution-evidence`. The tree was clean before edits; the branch
was not main. `concord-pass-a-c1-c2-public` resolved to exactly that starting SHA.
Startup branch/status/HEAD/log/tag checks all passed. No merge, push or tag action
was performed.

Implementation and final clean-reproduction commit identities will be recorded after
the reviewed implementation commit exists. Development reproductions are honestly
dirty runs, not execution from a future implementation commit. A separate evidence-
only commit will retain actual clean-commit run instances. The first commit closes
the tested implementation; it does not pretend those development runs were clean.

## Exact files changed

Implementation/document/test commit:

```text
.github/workflows/pass-a.yml
PASS_B_EVIDENCE.md
README.md
docs/PASS_B_USAGE.md
examples/synthetic/pass_b_fixture.py
examples/synthetic/pass_b_splits.json
pyproject.toml
scripts/reproduce_pass_b.py
src/concord/c3_cli.py
src/concord/c3_contracts.py
src/concord/c3_storage.py
src/concord/cli.py
src/concord/evaluation/failures.py
src/concord/evaluation/quality.py
src/concord/features/reference.py
src/concord/inference/resolution.py
src/concord/modeling/scorer.py
src/concord/modeling/training.py
tests/test_c3_cli.py
tests/test_c3_features.py
tests/test_c3_resolution.py
tests/test_c3_training_storage.py
```

The subsequent evidence-only commit updates this document and adds
`docs/evidence/PASS_B_RUNS.json`. No bulk output or model artifact is staged.

## Scope and preserved boundaries

C3 implements immutable FeatureRow, ScoredCandidate, OwnershipResult,
CandidateDisposition, ResolutionDecision, FailureAttribution and
ResolutionEvidenceRecord boundaries. It adds the 59-feature reference engine,
explicit negative mining/splits, a thin scorer and LightGBM implementation, global
ownership, frozen decoder, set evaluation, calibration, policy-stage attribution,
typed Parquet, compact evidence and gated train/resolve/evaluate CLI surfaces.

No retrieval candidate generation was added to C3. It consumes validated completed
C2 runs and recomputes coordinate-only feature cosines on the supplied bounded graph.
Historical source, historical manifests, the original six tests, accepted retrieval
implementation and Pass A evidence are preserved. The accepted Pass A tag is unchanged.
No private input, model weights, bulk outputs, caches, environments or temporary
scripts are committed. The new LightGBM model is generated only under ignored outputs.

## Feature schema and public parity

Exactly 59 ordered definitions; schema version `concord.features.historical-59.v1`.
SHA-256: `6450b326649beb45e9b9ac7d5a0617934a1c9b21c7ca1f5a12c8b9a3c92ba6f8`.
Names match the preserved ordered schema. The new identity hashes ordered names,
definitions and their versions; it is not the historical physical schema-file hash.
It is sensitive to order/name/definition/version changes and independent of dtype.
Public values are immutable finite tuples; float32 conversion is confined to the
batch/model boundary. Typed feature storage preserves float64 values.

Public parity tests execute preserved direct and cross-feature functions on exact,
partial, missing/empty, Unicode, punctuation, numeric, acronym-like and cross-script
inputs. A full 59-value test executes the preserved worker and SQL window expressions
on an uncapped 200-query/200-target fixture, using a documented SQLite dialect adapter
for SQL execution and final float32 casts. It compares all 59 outputs exactly at the
historical numeric boundary, including graph context and lane-present/absent ranks.
This does not recreate historical private row order or model probabilities.

Compatibility adapters are explicit: None and empty remain distinct in entity
storage, while the historical numeric features use empty-input indicators for both;
C2 ranks become zero-based numeric feature ranks, and absent ranks use legacy 999
only inside the reference feature vector. C2 provenance retains absent/null lanes.
Private capped sample membership and full historical graph parity remain UNVERIFIED.

## Split discipline and negative mining

The committed invented fixture has explicit entity-disjoint membership:

| Split | Queries | Targets | Role |
|---|---:|---:|---|
| train | 240 | 480 | training only |
| calibration | 12 | 24 | independent descriptive calibration |
| test | 16 | 21 | independent public fixture evaluation |

The split plan fixes the full logical dataset and exactly covers its identities.
Each split has independent C2 retrieval, vectorizer fitting and graph-context features.
Neither held-out records nor held-out truth enters training. Evaluation rejects train
membership; model provenance must match the declared training group and split plan.

`concord.top-retrieval-hard-negatives.v1` keeps retrieved training truths and up to
16 retrieved non-truth pairs per query, ordered by maximum lane similarity with
seed-42 content-hash ties. Mining seed 42 is an explicit new configuration. Every
mined row retains its reason, graph/retrieval/split/mining identities. Unretrieved
truths are counted but never inserted into the graph. Labels are assumed complete
within the declared split; this policy is unsuitable for unknown/incomplete labels.

Development reproduction measured 5,290 training candidates, 240 retrieved positives
and 3,670 selected negatives. Both classes enter training; no Cartesian negatives are
created. Final measured values will be tied to the clean-run bundle.

## Model, calibration, ownership and decoder

The thin scorer uses fit/predict_proba/get_params/fingerprint and returns probabilities.
It contains no ownership, decoder or attribution policy. LightGBM 4.7.0 uses the
historical/reference 600 estimators, learning rate .05, 63 leaves, min_child_samples
100, L2 1.0, full row/column sampling, no class weights and no early stopping.
Seed provenance is `DEFAULTED_TO_42_NO_PRIOR_VALUE_FOUND`; original historical seed
recovery is not claimed. Single-threaded deterministic column-wise execution is an
explicit new portability setting. Development reproduction fitted 600 actual trees.

Model identity retains format, artifact hash, model config, ordered schema, training
dataset/split/plan, mining/pair identities, feature artifact, retrieval config,
LightGBM/NumPy versions and actual trees. Paths are not identities. Loading verifies
model bytes, metadata identity, library version, configuration and feature order.
Within-platform repeat checks cover model bytes and logical scores/resolutions;
cross-platform model-byte equality is not assumed.

Calibration reports describe retrieved held-out pairs with AUROC/AUPRC, log loss,
Brier, fixed bins/ECE and score distributions. Absent-class/empty metrics are null.
Slope/intercept are unestimated; no calibration transform or threshold tuning occurs.
These tiny fixtures cannot establish general calibration or model performance.

Ownership is global within the declared candidate population: score DESC, s1_id ASC,
exactly one rank-1 owner per target. Owner rival is the runner-up; loser rival is the
winner. Singleton rival/margin is undefined. Decoding is exactly owner and score >=
0.640. NONE, BELOW_THRESHOLD and LOST_OWNERSHIP are retained; SET_POLICY is reserved
and never fabricated. Every S1 has a sorted immutable zero/one/many accepted set.

## Quality and stage attribution

Quality is macro per-S1 set F0.5/precision/recall, exact-set accuracy and truth-based
zero/single/multi cohorts. Empty/empty has P=R=F=1; empty truth/nonempty prediction
has P=F=0,R=1; nonempty truth/empty prediction has P=R=F=0. Empty cohorts are undefined.

The executed development test fixture measured macro F0.5 0.6145833333333334,
precision 0.625, recall 0.71875, exact-set accuracy 0.5625, and 12 accepted links over
16 queries. These are invented P0 observations, not benchmark or private results.
Final values and provenance will be recorded from clean runs.

False-negative precedence is RETRIEVAL, SCORING below .640, OWNERSHIP loss, DECODING
mis-emission of an admissible owner. Genuine explicit label/data ambiguity is separate;
missing artifacts cause validation errors. Admissible false positives are SCORING;
score-ineligible/out-of-graph emission is DECODING. This is policy-stage attribution,
not causal proof. The public fixture includes an explicit conflicting-label pair;
ordinary mistakes are not automatically called ambiguous.

Development FN counts were retrieval 1, scoring 2, ownership 1, explicit ambiguity 1,
decoding 0. Both FPs were scoring. DECODING is tested with a simulated emission defect;
the historical baseline adds no set exclusion merely to manufacture a nonzero count.

## Resolution Evidence Capsule and lineage

Capsules retain decision/set, candidate count, top score, minimum accepted lane count,
alternate-lane availability, minimum ownership/threshold margin and second/best score
ratio. Undefined values remain None, including accepted diagnostics on zero-match.
Singleton rivals make the accepted-set minimum ownership margin undefined. No
is_stable, counterfactual robustness or C4 stability study is implemented.
Explain uses actual artifacts and at most five rejected competitor records.

All C3 bulk products have strict typed Parquet schemas. Schema/config/manifest/report
metadata and capsules use canonical JSON. Artifact parents connect dataset,
normalization, C2 graph/freeze, ordered features, mined labels, model, scores,
ownership, dispositions, sets, evaluation and evidence. External parents connect
separate training/resolution/evaluation runs; content DAG validation preserves
multiple producing observations of identical content. Consumed artifacts are hash-
and size-checked. FAILED manifests use the original-exception-preserving validated
Pass A failure path.

## Verification and development failures

Final complete Windows suite: **189 passed, 0 failed, 0 skipped**, 328.96 seconds,
native Windows 11 build 26200 / Python 3.12.10. Actual Ubuntu/WSL suite: **189 passed,
0 failed, 0 skipped**, 325.11 seconds, Python 3.12.3 on Ubuntu/glibc 2.39,
kernel `6.18.40.1-microsoft-standard-WSL2`. The totals include 109 accepted Pass A
cases (six original historical tests) and 80 C3 cases. No configured CI
run is counted as Linux execution. The Windows/Ubuntu workflow also includes C3
reproduction, but has not run remotely because no push occurred.

Both platforms passed Ruff and compileall. `git diff --check` and protected-path
diff checks passed. All C3 CLI commands executed through the full public reproduction
inside both complete suites; separate Windows and Ubuntu development reproductions
also completed. The fixture's 18 run manifests per platform validate, and artifact
hashes/lineage were tested. No private parity was performed.

```powershell
.venv\Scripts\python.exe -m pytest -q --tb=short
wsl -d Ubuntu --exec /var/tmp/concord-pass-a-closure-venv/bin/python -m pytest -q --tb=short
.venv\Scripts\python.exe -m ruff check src/concord --exclude legacy_amazon tests scripts examples/synthetic/pass_b_fixture.py
wsl -d Ubuntu --exec /var/tmp/concord-pass-a-closure-venv/bin/python -m ruff check src/concord --exclude legacy_amazon tests scripts examples/synthetic/pass_b_fixture.py
.venv\Scripts\python.exe -m compileall -q src/concord tests scripts examples/synthetic/pass_b_fixture.py
wsl -d Ubuntu --exec /var/tmp/concord-pass-a-closure-venv/bin/python -m compileall -q src/concord tests scripts examples/synthetic/pass_b_fixture.py
.venv\Scripts\python.exe scripts/reproduce_pass_b.py --output outputs/pass-b-windows-development
wsl -d Ubuntu --exec /var/tmp/concord-pass-a-closure-venv/bin/python scripts/reproduce_pass_b.py --output outputs/pass-b-linux-development
```

Executed targeted checks: feature suite 16 passed; resolution/attribution/calibration
suite 27 passed. The first combined training/storage/CLI check had 36 pass / 1 fail:
Parquet canonicalizes nested list child names, so inferred tag-list names differed
from strict schema identity. The new schema now explicitly uses the Parquet child
name with non-null elements; validation was not weakened. The targeted seven typed
stage round-trips then passed. A deliberately overflowing numeric feature is rejected
at the float32 boundary; its expected warning is asserted by the test.

Development also exposed repeated recomputation of immutable split/schema hashes;
those identities are computed once per operation. This changes no sampling or numeric
semantics. Ruff import/default-binding findings were corrected only in new code.

Warnings remain visible: the existing Windows pytest-asyncio fixture-scope warning,
and LightGBM messages about no further positive-gain splits on small fixture data.
Reproduction stderr logs retain model messages; no warning is hidden by unrelated
configuration changes. Resource counters are stage smoke observations after input/
parent verification, not throughput or isolated-memory benchmarks.

## Claim boundary and C4 prerequisites

PUBLIC_PASS is public function/schema/policy/end-to-end evidence only. Private feature
values, historical model probabilities and private Amazon output parity were not
tested. No WDC, leaderboard improvement, private capped-sampling parity, historical
scale, external superiority, or stability claim is made. Preserved historical
leaderboard evidence remains historical; no removed rank value is reintroduced.

C4 still requires separately authorized public benchmark variants, same/cross-script
and OOD studies, retrieval challengers, stability-vs-confidence design/statistics,
drift, Failure Atlas, scale measurements and release gates. Nothing in this pass
starts that work. Replay and unfinished C4 CLI surfaces remain unexposed.

Usage and conventions: [PASS_B_USAGE.md](docs/PASS_B_USAGE.md).
