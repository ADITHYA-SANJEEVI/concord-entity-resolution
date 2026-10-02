# PASS B EVIDENCE — C3

## Status, branch and checkpoint

**PASS — C3 PUBLIC_PASS.** No C4 work is included.
Starting SHA: `70abb57241b246bec4fcee5b26e672735588e46f`.
Branch: `c3/scoring-resolution-evidence`. The tree was clean before edits; the branch
was not main. `concord-pass-a-c1-c2-public` resolved to exactly that starting SHA.
Startup branch/status/HEAD/log/tag checks all passed. No merge, push or tag action
was performed.

Implementation commit: `fd875dbd7e1a26ea1616f2b740a8c79b87d13e49`.
The tree was clean before both final public reproductions and remained clean until
both completed. All **36 COMPLETED manifests** (18 per platform) identify that
implementation SHA and **dirty=false**. Only afterward were this document and the
new bundle updated for the separate evidence-only commit. No source changed after
the producing implementation commit. Development runs remain honestly dirty local
artifacts and are not relabelled as clean evidence.

Current evidence: [PASS_B_RUNS.json](docs/evidence/PASS_B_RUNS.json), **889,369 bytes**.
It retains unmodified clean manifest instances, physical/logical manifest hashes,
actual reproduction summaries, eight actual capsule examples and local bulk-artifact
pointers. It contains metadata/reports, not model weights or bulk feature/candidate
tables. The collector validated every artifact's physical hash and size, all recorded
source hashes, summary-to-report consistency and clean producing identities.

```powershell
.venv\Scripts\python.exe scripts/reproduce_pass_b.py --output outputs/pass-b-windows-clean
wsl -d Ubuntu --exec /var/tmp/concord-pass-a-closure-venv/bin/python scripts/reproduce_pass_b.py --output outputs/pass-b-linux-clean
.venv\Scripts\python.exe tmp/collect_pass_b_evidence.py
```

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

The evidence-only commit updates this document and adds
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

Clean reproduction measured 5,290 training candidates, 240 retrieved positives
and 3,670 selected negatives. Both classes enter training; no Cartesian negatives are
created. These values match both platforms and are retained in the clean-run bundle.

## Model, calibration, ownership and decoder

The thin scorer uses fit/predict_proba/get_params/fingerprint and returns probabilities.
It contains no ownership, decoder or attribution policy. LightGBM 4.7.0 uses the
historical/reference 600 estimators, learning rate .05, 63 leaves, min_child_samples
100, L2 1.0, full row/column sampling, no class weights and no early stopping.
Seed provenance is `DEFAULTED_TO_42_NO_PRIOR_VALUE_FOUND`; original historical seed
recovery is not claimed. Single-threaded deterministic column-wise execution is an
explicit new portability setting. Both clean reproductions fitted 600 actual trees.

Model identity retains format, artifact hash, model config, ordered schema, training
dataset/split/plan, mining/pair identities, feature artifact, retrieval config,
LightGBM/NumPy versions and actual trees. Paths are not identities. Loading verifies
model bytes, metadata identity, library version, configuration and feature order.
Within-platform repeat checks cover model bytes and logical scores/resolutions;
cross-platform model-byte equality is not assumed.

The observed model artifact SHA-256 is
`56c7835ce07f19cdf0f64f8a28e41066fa91f3d39c93acb3856d380c6f9acdb8`;
its full model identity is
`9e536cf25f63161b20ed2b1d75d3180a558d3e10b6543f1ce8cb6373d13a56e7`.
Those actual identities matched in these runs, without a framework-level guarantee
of future cross-platform byte identity.

Calibration reports describe retrieved held-out pairs with AUROC/AUPRC, log loss,
Brier, fixed bins/ECE and score distributions. Absent-class/empty metrics are null.
Slope/intercept are unestimated; no calibration transform or threshold tuning occurs.
These tiny fixtures cannot establish general calibration or model performance.

| Retrieved-pair population | Pairs | AUROC | AUPRC | Log loss | Brier | ECE |
|---|---:|---:|---:|---:|---:|---:|
| P0/pass-b-v1/calibration/retrieved-pairs | 220 | 0.8976190476190476 | 0.7202020202020202 | 0.1414498631721216 | 0.013634383826212428 | 0.01361637625036344 |
| P0/pass-b-v1/test/retrieved-pairs | 218 | 0.9236694677871149 | 0.7438681894776259 | 0.18199038229368325 | 0.018344858615228003 | 0.018324438030941345 |

Both platforms produced these executed values; raw reliability bins/distributions
and class counts are retained in the bundle. They describe retrieved pairs, so the
retrieval miss is not silently counted as a scored negative. Pair quality is separate
from set quality.

Ownership is global within the declared candidate population: score DESC, s1_id ASC,
exactly one rank-1 owner per target. Owner rival is the runner-up; loser rival is the
winner. Singleton rival/margin is undefined. Decoding is exactly owner and score >=
0.640. NONE, BELOW_THRESHOLD and LOST_OWNERSHIP are retained; SET_POLICY is reserved
and never fabricated. Every S1 has a sorted immutable zero/one/many accepted set.

## Quality and stage attribution

Quality is macro per-S1 set F0.5/precision/recall, exact-set accuracy and truth-based
zero/single/multi cohorts. Empty/empty has P=R=F=1; empty truth/nonempty prediction
has P=F=0,R=1; nonempty truth/empty prediction has P=R=F=0. Empty cohorts are undefined.

The executed clean test fixture measured macro F0.5 0.6145833333333334,
precision 0.625, recall 0.71875, exact-set accuracy 0.5625, and 12 accepted links over
16 queries. These are invented P0 observations, not benchmark or private results.
Both platforms measured the same values from the clean producing commit.

| Query population | Queries | Macro F0.5 | Macro precision | Macro recall | Exact-set accuracy | Accepted links |
|---|---:|---:|---:|---:|---:|---:|
| P0/pass-b-v1/calibration | 12 | 0.75 | 0.75 | 0.8333333333333334 | 0.75 | 9 |
| P0/pass-b-v1/test | 16 | 0.6145833333333334 | 0.625 | 0.71875 | 0.5625 | 12 |

Test truth-cohort F0.5: zero-match 0.3333333333333333 over 3 queries, single-match
0.6363636363636364 over 11, multi-match 0.9166666666666667 over 2. Prediction decision
counts are separately zero 5, single 10, multi 1. Test totals are TP 10 / FP 2 / FN 5;
truth ambiguity is deliberately retained rather than removed to improve metrics.

False-negative precedence is RETRIEVAL, SCORING below .640, OWNERSHIP loss, DECODING
mis-emission of an admissible owner. Genuine explicit label/data ambiguity is separate;
missing artifacts cause validation errors. Admissible false positives are SCORING;
score-ineligible/out-of-graph emission is DECODING. This is policy-stage attribution,
not causal proof. The public fixture includes an explicit conflicting-label pair;
ordinary mistakes are not automatically called ambiguous.

Clean test FN counts were retrieval 1, scoring 2, ownership 1, explicit ambiguity 1,
decoding 0. Both FPs were scoring. DECODING is tested with a simulated emission defect;
the historical baseline adds no set exclusion merely to manufacture a nonzero count.
Examples: `test-miss` loses its truth at retrieval, `test-below` at scoring,
`test-own-z` at ownership, `test-amb-z` has explicitly conflicting labels. False
positives `test-own-a` and `test-phantom` receive admissible non-match scores.

## Resolution Evidence Capsule and lineage

Capsules retain decision/set, candidate count, top score, minimum accepted lane count,
alternate-lane availability, minimum ownership/threshold margin and second/best score
ratio. Undefined values remain None, including accepted diagnostics on zero-match.
Singleton rivals make the accepted-set minimum ownership margin undefined. No
is_stable, counterfactual robustness or C4 stability study is implemented.
Explain uses actual artifacts and at most five rejected competitor records.

Actual clean capsule examples (identical between platforms):

| S1 | Decision | Candidates | Top score | Minimum accepted lanes | Ownership / threshold margin |
|---|---|---:|---:|---:|---|
| test-empty | zero_match, empty set | 0 | None | None | None / None |
| test-own-z | zero_match, empty set | 14 | 0.9998072758773955 | None | None / None |
| test-q-000 | single_match, test-t-000 | 18 | 0.9998072758773955 | 5 | 0.9997946564090704 / 0.35980727587739547 |
| test-multi | multi_match, test-multi-one/two | 14 | 0.9998072758773955 | 5 | 0.9997946564090704 / 0.35980727587739547 |

The high-scoring zero-match illustrates ownership loss without conflating score
with acceptance. `test-multi` has ambiguity ratio 1.0 and alternate-lane availability
true, without assigning a stability label. Full identity fields are retained in
the eight bundled platform examples and original evidence artifacts.

All C3 bulk products have strict typed Parquet schemas. Schema/config/manifest/report
metadata and capsules use canonical JSON. Artifact parents connect dataset,
normalization, C2 graph/freeze, ordered features, mined labels, model, scores,
ownership, dispositions, sets, evaluation and evidence. External parents connect
separate training/resolution/evaluation runs; content DAG validation preserves
multiple producing observations of identical content. Consumed artifacts are hash-
and size-checked. FAILED manifests use the original-exception-preserving validated
Pass A failure path.

## Reproducibility identities and smoke resources

| Identity | SHA-256 |
|---|---|
| Full invented dataset | 9c65ea880f280c04f27a5a0e0d8a706ab361c2dc83766e2a6eeb1a33127fd8f0 |
| Committed split plan | a05137bc525bd118687fd92daa7b2fc2297609be31b82fdacdc1f4b648f9ae9f |
| Train split | 3e280d2192e188147aef7a3db698fd9019ad31eb40f9bfac45bd2805434242ed |
| Calibration split | e07b2649d5e96bd8955f9537cafb4a3a9d1fc318f64803335dc3a6722178444c |
| Test split | 9445e886b350632a0a3c71917fccbc8e346088a8e36568523358354a40a193d2 |
| Retrieval configuration (explicit synthetic profile) | ba796fe2a90f2c2141bd548d3f8d26eab3f9b5f1a13787045ad2ffb68dd20940 |
| Decoder configuration | 074e17bcdcd1687f88f050be540c4e7464c9ad87e7092192134a6d3a902ec46b |
| Test bounded candidate graph | c27c5ed1546efe7e220aa757490d99e221976a7f12dcb647b6c80027bc15a922 |
| Test logical scores (excluding model/path fields) | dd8d71a5b86ae492b5600902e28f47be9a2d88e4bfc2589af56448ef4c90cb7a |
| Test resolution sets | 13ee550e045ab5b4cbf4e7e3acb9d2aa467b010e3c0747ee7c43ab516c717215 |

All these identities matched across platforms. Within-platform model fits and
score/set repeats matched. Both calibration/test logical score fingerprints matched
exactly across these platform runs, as did set quality and attribution reports;
calibration values also matched within 1e-12. This is an observed fixture result,
not a universal LightGBM portability guarantee.

| Clean test resolution | Wall seconds | CPU seconds | OS peak RSS bytes | End sampled RSS bytes | Artifact bytes |
|---|---:|---:|---:|---:|---:|
| Windows | 8.067018999994616 | 6.53125 | 185,069,568 | 184,020,992 | 103,497 |
| Ubuntu WSL | 5.89211217299453 | 3.4354262139999996 | 229,765,120 | 230,825,984 | 103,497 |

These are actual smoke observations, including stage artifact generation after
parent/input verification. Separate OS RSS accounting snapshots can disagree;
both are retained. They are not platform-speed comparisons or scale evidence.

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
Each clean fit emitted 600 no-further-positive-gain-split messages on each platform;
these nonfatal messages remain in ignored stderr logs. Actual fitted tree count is
600, and the complete suites pass.

The final staged audit checked an exact 22-file implementation allowlist, UTF-8,
credential patterns, file sizes under 1 MiB and protected-path/tag preservation.
The evidence-only audit checks that its only files are this document and the new
bundle, verifies retained instances against original output files, and proves no
source drift from the producing commit. No private/binary/bulk artifacts are staged.

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
