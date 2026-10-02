# PASS A EVIDENCE

## Original Pass A status and starting checkpoint

**PASS — PUBLIC_PASS for C1 and C2.** C3 has not been started. No push was performed.

Starting SHA: `812f0a31d6d2d1616d69e9be6147d62b970eed38`.
The initial `git status --short` was empty, and HEAD was exactly the requested
checkpoint. `git merge-base --is-ancestor 812f0a3 HEAD` succeeded.

The historical freeze was read first, followed by the authoritative v1.1 amendment,
flagship specification, data contract, experiment/benchmark contract, and gated plan.
Historical source was inspected for normalization, vectorizers, combined weighting,
sampling, sparse top-N, reverse direction, rank indexing, and mask semantics.

## Narrow closure: parity claim boundary

Closure starting SHA: `3b39bab66ae16d613c746e76fb0bd93b07250d23`.
Its working tree was clean. The legacy trees, historical manifests, and original six
tests were unchanged against the original `812f0a3` checkpoint.

**HISTORICAL PARAMETER / FUNCTION PARITY:** non-null normalization, vectorizer
parameters, and five-view sparse function/reference behavior on uncapped fixtures
are supported. Canonical seeded sampling is deterministic.

**UNVERIFIED PRIVATE CAPPED-SAMPLE / FULL-GRAPH PARITY:** the preserved sampler uses
historical q/t materialization order; new Concord sorts by `(source, entity_id)` before
sampling, queries then targets. Above FIT_CAP=3,000,000, identical RNG positions do
not prove equal sample membership. Historical capped membership and exact historical-scale
candidate-graph parity have not been reproduced and are not claimed.

The immutable `sampling_order_policy` (`concord.source-id.queries-then-targets.v1`)
is fingerprinted in config/manifests and repeated in per-fit evidence with population,
sample counts, cap status, and an explicit `UNVERIFIED` historical capped-parity field.
Tests use the real numeric FIT_CAP boundary and the actual preserved sampler on an
explicitly reduced-cap, synthetic reordered population. They demonstrate differing
membership above the cap without inventing private order or calling self-comparison
historical parity.

Empty-vocabulary handling is the fingerprinted `concord.warn-empty-lane.v1` new
Concord compatibility/fail-safe adapter. The preserved fitter raises; new Concord
retains warnings and empty lanes. No DF relaxation or Cartesian fallback is added.
This divergence is not exact legacy execution parity.

The CLI validates `FAILED` manifests before their final write. Secondary validation
or diagnostic-write failures are reported while preserving the original exception.
Invalid snapshots are explicitly labelled and do not overwrite validated evidence.

Closure verification: the complete Windows suite passed **109/109** in 87.68 seconds;
the complete Ubuntu/WSL suite passed **109/109** in 91.98 seconds. This includes the
original six unchanged tests and 103 new-contract tests, including 11 added closure
cases. Ruff, compileall, `git diff --check`, and protected-path diff checks passed on
the applicable platforms. The existing Windows pytest-asyncio configuration warning
does not change the test result.

Windows commands: `.venv/Scripts/python.exe -m pytest -q --tb=short`,
`-m ruff check src/concord --exclude legacy_amazon tests scripts examples/synthetic/pass_a_fixture.py`,
and `-m compileall -q src/concord tests scripts`.
Ubuntu commands used the same arguments through `wsl -d Ubuntu --exec
/var/tmp/concord-pass-a-closure-venv/bin/python`. Python versions remain Windows
3.12.10 and Ubuntu 3.12.3.

The implementation/document/test correction is committed first. Clean reproduction
and its producing SHA will be recorded in a subsequent evidence-only commit. Until
then, the bundle and measured results below are the original development evidence,
with their original dirty-run provenance; no earlier manifest is relabelled clean.

## Implementation scope

C1 implements immutable typed records, explicit missing/empty semantics, opaque IDs,
optional country labels, versioned normalization, logical dataset/split fingerprints,
canonical UTF-8 metadata, typed Parquet, manifest/schema separation, content DAG
primitives, and `concord inspect profile|schema|fingerprint`.

C2 implements the frozen five-view reference configuration, separate retrieval text
views, bounded sparse products, immutable lane evidence, deterministic candidate
union, masks, typed candidate Parquet, retrieval diagnostics, frontier data/plots,
and `concord retrieve run|frontier|lane-rescue|ablate`.

The synthetic fixture profile is explicitly separate and never silently substitutes
for historical DF settings. No challenger, feature engine, training, ownership,
decoder, evidence capsule, stability experiment, or C4 release benchmark is included.

## Original Pass A files changed

```text
.github/workflows/pass-a.yml
.gitignore
PASS_A_EVIDENCE.md
README.md
docs/PASS_A_USAGE.md
docs/evidence/PASS_A_RUNS.json
examples/synthetic/pass_a_fixture.py
pyproject.toml
scripts/reproduce_pass_a.py
src/concord/__main__.py
src/concord/cli.py
src/concord/contracts.py
src/concord/identity.py
src/concord/inspection.py
src/concord/metadata.py
src/concord/normalization.py
src/concord/retrieval/analysis.py
src/concord/retrieval/baseline.py
src/concord/retrieval/plotting.py
src/concord/schemas/experiment.schema.json
src/concord/storage.py
tests/conftest.py
tests/test_cli.py
tests/test_foundation.py
tests/test_retrieval.py
```

The original two test files, all `legacy_amazon` files, historical manifests,
architecture bundle, and existing TSV fixtures are unchanged.

## Verification commands

All commands were executed from the repository unless a Linux path is explicit.
Repeated commands below represent the same checks after fixes, rather than additional
independent quality measurements.

```powershell
git status --short
git rev-parse HEAD
git merge-base --is-ancestor 812f0a3 HEAD
python --version
python -m pytest -q
python -m pip install -e '.[dev]'
python -m venv --system-site-packages .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe -m pytest tests/test_foundation.py tests/test_retrieval.py -q --tb=short
.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -k frontier -q --tb=short
.\.venv\Scripts\python.exe -m pytest -q --tb=short
.\.venv\Scripts\python.exe -m ruff check src/concord --exclude legacy_amazon tests scripts examples/synthetic/pass_a_fixture.py
.\.venv\Scripts\python.exe -m compileall -q src/concord tests scripts
.\.venv\Scripts\python.exe scripts/reproduce_pass_a.py --output outputs/pass-a-windows
.\.venv\Scripts\python.exe scripts/reproduce_pass_a.py --output outputs/pass-a-windows-final
.\.venv\Scripts\python.exe scripts/reproduce_pass_a.py --output outputs/pass-a-windows-verified
wsl --list --quiet
wsl -d Ubuntu --exec sh -lc 'python3 --version; uname -a; command -v uv; command -v pip3'
wsl -d Ubuntu --exec python3 /mnt/c/Users/adith/OneDrive/Desktop/concord-entity-resolution/tmp/virtualenv.pyz /tmp/concord-pass-a-venv
wsl -d Ubuntu --exec /tmp/concord-pass-a-venv/bin/python -m pip install -e /mnt/c/Users/adith/OneDrive/Desktop/concord-entity-resolution[dev]
wsl -d Ubuntu --exec /tmp/concord-pass-a-venv/bin/python -m pytest -q --tb=short
wsl -d Ubuntu --exec /tmp/concord-pass-a-venv/bin/python -m ruff check src/concord --exclude legacy_amazon tests scripts examples/synthetic/pass_a_fixture.py
wsl -d Ubuntu --exec /tmp/concord-pass-a-venv/bin/python -m compileall -q src/concord tests scripts
wsl -d Ubuntu --exec /mnt/c/Users/adith/OneDrive/Desktop/concord-entity-resolution/.venv-linux/bin/ruff check src/concord --exclude legacy_amazon tests scripts examples/synthetic/pass_a_fixture.py
wsl -d Ubuntu --exec python3 -m compileall -q src/concord tests scripts
wsl -d Ubuntu --exec /tmp/concord-pass-a-venv/bin/python scripts/reproduce_pass_a.py --output outputs/pass-a-linux-final
wsl -d Ubuntu --exec /tmp/concord-pass-a-venv/bin/python scripts/reproduce_pass_a.py --output outputs/pass-a-linux-verified
.\.venv\Scripts\python.exe tmp/review_plot.py
.\.venv\Scripts\python.exe tmp/collect_evidence.py
.\.venv\Scripts\python.exe tmp/audit_staged.py
.\.venv\Scripts\concord.exe --help
git diff -- src/concord/legacy_amazon archive_manifest tests/test_preserved_contract.py tests/test_manifests.py
git diff --cached --stat
git diff --cached -- pyproject.toml .gitignore README.md .github/workflows/pass-a.yml
git diff --cached --check
git diff --check
```

Temporary scripts and environments are ignored. `collect_evidence.py` validated
all 12 retained manifests, each artifact's physical hash, and every recorded new-code
source hash against the final implementation. It verified identical logical candidate
hashes for all six paired Windows/Linux runs. `review_plot.py` rendered a PNG from the
measured frontier; visual inspection led to grouping overlapping labels in legends.
The generated SVGs and Parquet artifacts remain in the local output directories.
The final staged audit verified the exact 25-file allowlist, preserved source/tests,
UTF-8 decoding without replacement characters, absence of credential patterns, no
bulk-data files, and no staged file above 1 MiB. The final diff was reviewed for scope.

Ruff fixes were limited to new files. Existing test import-spacing findings were
explicitly excluded to preserve the historical tests. No type checker is configured
by the original repository; runtime validators, syntax compilation, and Ruff were run.

## Complete test totals and retained failures

| Execution | Passed | Failed | Skipped | Result |
|---|---:|---:|---:|---|
| Initial historical Windows suite | 6 | 0 | 0 | PASS |
| Initial expanded Windows suite | 94 | 4 | 0 | FAIL; corrected below |
| Foundation + retrieval after corrections | 81 | 0 | 0 | PASS |
| Corrected complete Windows suite | 98 | 0 | 0 | PASS |
| Initial complete Linux suite | 97 | 1 | 0 | FAIL; corrected below |
| Final complete Windows suite | 98 | 0 | 0 | PASS, 97.73 seconds |
| Final complete Ubuntu WSL suite | 98 | 0 | 0 | PASS, 90.26 seconds |

The final suite contains **6 preserved historical tests + 92 C1/C2 tests**, including
parametrized cases. Both final platforms ran the entire repository suite.

The initial Windows failures were: duplicate content hashes in frontier lineage;
a test trying to write illegal non-nullable Parquet; an incorrect synthetic missingness
expectation; and the parity harness omitting the preserved `commit()` helper. The
lineage implementation was corrected to merge content nodes while preserving producing
observations; the other three were test corrections. A targeted frontier rerun still
showed the original lineage failure before that correction completed.

The Linux failure was an invalid test assumption that `getrusage.ru_maxrss` must always
be at least psutil's sampled RSS. Linux's separate OS accounting snapshots disagreed.
Both observed metrics remain unchanged; the test now checks valid positive measurements.
This is not a modification of results to manufacture a passing comparison.

The global Windows environment emits a third-party `pytest_asyncio` fixture-scope
deprecation warning. No Concord async tests depend on that plugin. It is retained
here rather than hidden by an unrelated configuration change.

The first Windows pip attempt was blocked by sandbox network access; the repository
environment installation succeeded with escalation. WSL enumeration was initially
denied inside the sandbox and succeeded with escalation. Ubuntu had Python 3.12.3
but no ensurepip/venv package. A virtualenv bootstrap was downloaded to ignored `tmp/`.
One bootstrap attempt failed because Windows-to-shell quoting stripped Python code.
A repository-mounted environment was too slow; its verified pip process was stopped
after the `/tmp` environment successfully installed the same declared dependencies.
These setup failures do not constitute Linux verification; the actual completed tests do.
After those completed tests, a further Ruff invocation found the ephemeral `/tmp`
environment absent. Final Linux Ruff then passed using the repository-local standalone
binary, and final Linux compileall passed with system Python. The successful suite and
measurement results above were completed while the `/tmp` environment existed.

## C1 acceptance matrix

| Requirement | Evidence | Acceptance |
|---|---|---|
| Immutable typed entity/normalized contracts | Frozen slots; validated scalar fields; mutation tests | PASS |
| None distinct from empty | Normalization, hashes, profiles, Parquet, retrieval flags | PASS |
| Opaque IDs; optional opaque country | No prefix inference; explicit source validation | PASS |
| Deterministic versioned normalization | Exact non-null `fold()` parity; Unicode database version in identity | PASS |
| Unicode parity | Composed/decomposed, accents, ligatures, full-width, multiple scripts | PASS |
| Logical dataset identity | SHA-256; canonical source/ID order; duplicate rejection; reordered Parquet test | PASS |
| Split identity | Dataset/name/purpose/membership/cohort metadata; order invariance | PASS |
| Canonical metadata | UTF-8, sorted keys, null distinction, finite JSON, typed keys | PASS |
| Entity and normalized Parquet | Versioned schemas, zstd, nullability, empty-table/Unicode round trips | PASS |
| Manifest instance/schema separation | Packaged Draft 2020-12 schema; instance/config/metric/artifact/DAG validation | PASS |
| Artifact lineage | Immutable records, producing config/commit, external parents, cycle checks | PASS |
| Inspect CLI | profile/schema/fingerprint; public TSV adapter and split membership tests | PASS |
| Native Windows + Linux | Entire suite and public reproduction on both platforms | PASS |
| Linux CI path | Windows/Ubuntu Python 3.12 workflow configured | CONFIGURED; not executed remotely |
| Historical regression | Original six tests unchanged and passing | PASS |

## C2 acceptance matrix

| Requirement | Evidence | Acceptance |
|---|---|---|
| Views separate from normalization | Immutable RetrievalTextViews; ASCII-space compact parity; missingness flags | PASS |
| Frozen five-view baseline | Exact vectorizer parameters; `(5,5,5,10,8)`; equal-weight combined; reverse direction | PASS |
| Historical parameter/function/reference parity | AST-loaded preserved functions; uncapped real-text pair/similarity parity; explicit rank adapter | PASS |
| Canonical capped sampling | Versioned source/ID order, population/cap evidence; preserved sampler order-boundary test | DETERMINISTIC; private capped membership/full graph UNVERIFIED |
| Empty-vocabulary adapter | New Concord warns/emits empty lanes; preserved fitter raises | EXPLICIT DIVERGENCE |
| Bounded sparse retrieval | Chunked sparse-dot-topn only; global degree bound; no Cartesian fallback | PASS |
| Immutable per-lane provenance | One-based ranks; finite similarities; tuple evidence; validated mask | PASS |
| No missing-rank sentinel | Absent evidence / null flat Parquet rank and similarity | PASS |
| Deterministic union | Unique pairs; source/country conflicts rejected; canonical input/output; repeat hashes | PASS |
| Candidate cost and density | Pair count, mean/p50/p90/p99/max, zero-candidate rate, Reduction Ratio | PASS |
| Truth-pair recall and Recall@K | Executed labels; per-forward-lane and explicit union semantics; undefined uses null | PASS |
| Lane rescue/overlap | Candidate/truth overlap matrices, unique rescues, lane-count distribution, marginal cost | PASS |
| Leave-one-lane-out | Multi-lane candidates remain available; no final-resolution survival claim | PASS |
| Frontier | K 1/5/10/20; all configs retained; pair/runtime/RSS Pareto flags and reviewed SVG plots | PASS |
| Retrieve CLI | run/frontier/lane-rescue/ablate exercised on both platforms | PASS |
| Resources and lineage | Wall/CPU time, OS process peak + sampled RSS, bytes, environment, code hashes, artifact parents | PASS |
| Public retrieval report | 12 retained class-D synthetic run manifests and reports | PASS |
| Baseline/challenger separation | Baseline frozen; synthetic profile explicitly named; no challenger implemented | PASS |
| WDC adapter/config if practical | No dataset or exact variant supplied; P0 used for public acceptance | DEFERRED, optional |

## Actual measured retrieval results

All values below come from executed runs in [PASS_A_RUNS.json](docs/evidence/PASS_A_RUNS.json).
The bundle stores unmodified canonical manifest instances, reports, graph freezes,
manifest identities, and local artifact-directory pointers. Binary data products are
ignored in Git and reproducible from the committed invented fixture generator.

Runs were executed before the implementation commit. Their producing Git SHA is
the starting checkpoint and **dirty=true**, honestly identifying the uncommitted
implementation. Per-module source hashes were recorded and verified against the
final source. No manifest has been rewritten to claim execution from a later commit.

| Metric | P0 tiny fixture, synthetic profile | P0 strict historical-DF fixture |
|---|---:|---:|
| Queries / targets | 9 / 12 | 200 / 200 |
| Eligible comparisons | 48 | 40,000 |
| Candidate pairs | 12 | 272 |
| Truth pairs recovered / labelled | 8 / 9 | 200 / 200 |
| Truth-pair recall | 0.8888888888888888 | 1.0 |
| Reduction Ratio | 0.75 | 0.9932 |
| Density mean / p50 / p90 / p99 / max | 1.3333333333333333 / 1 / 2.2 / 2.92 / 3 | 1.36 / 1 / 1 / 9 / 9 |
| Zero-candidate count / rate | 2 / 0.2222222222222222 | 0 / 0 |
| Forward-lane union Recall@1 | 0.7777777777777778 | 1.0 |
| Forward-lane union Recall@5/10/20 | 0.8888888888888888 | 1.0 |

Populations: `P0/pass-a-fixture-v1/all-queries` and
`P0/pass-a-historical-df-fixture-v1/all-queries`, both `SYNTHETIC_PUBLIC`.
These metrics and logical candidate identities matched across Windows and Linux.
The tiny repeated-run candidate SHA-256 is
`0885be34394443ea3f3e146bcf4396d57cc351ea8616e9b9857463596c3ff40a`.

The tiny fixture retains one cross-script truth miss and two zero-candidate queries.
No transliteration gain is claimed. All five lanes have zero uniquely rescued truths
in this particular fixture; zero contributions are retained. Lane candidate counts
are name 8, compact 8, address 7, combined 12, reverse 12. Truths have lane counts
3:1, 4:4, 5:3. Dropping any single lane leaves the same 12 candidate pairs available.
Positive unique-rescue behavior is separately verified by the hand-labelled unit fixture.

The tiny frontier produced `(K, pairs, recall)` of `(1,10,8/9)`, `(5,12,8/9)`,
`(10,12,8/9)`, `(20,12,8/9)`. K=1 is nondominated on candidate cost; the others
are dominated on that cost in this fixture. No config is promoted and no general
quality or efficiency advantage follows from this tiny corpus.

| Platform / corpus | Retrieval wall seconds | CPU seconds | OS process peak RSS bytes | Sampled RSS bytes | Input / artifact bytes |
|---|---:|---:|---:|---:|---:|
| Windows / tiny | 0.05874920000496786 | 0.046875 | 166,707,200 | 165,986,304 | 2,993 / 18,297 |
| Windows / strict historical DF | 0.09341380000114441 | 0.078125 | 167,309,312 | 167,018,496 | 6,808 / 22,695 |
| Linux WSL / tiny | 0.056348867001361214 | 0.056310740999999886 | 237,834,240 | 238,702,592 | 2,993 / 18,297 |
| Linux WSL / strict historical DF | 0.0781825040030526 | 0.07778859500000035 | 239,386,624 | 240,709,632 | 6,808 / 22,695 |

Resource figures are smoke observations, not C4 scale benchmarks or platform-speed
comparisons. RSS includes the interpreter and dependencies. Runtime covers retrieval,
not CLI startup, serialization, evaluation, plotting, or manifest generation.

## Platform and historical verification

Native Windows: Windows 11 build 26200, Python 3.12.10, final 98/98 test pass;
Ruff and compileall passed; all public retrieval commands and repeated outputs succeeded.

Linux: actual Ubuntu WSL2 execution, kernel `6.18.40.1-microsoft-standard-WSL2`,
glibc 2.39, Python 3.12.3, final 98/98 test pass; Linux Ruff and compileall passed;
all public retrieval commands and paired logical output hashes succeeded. This is
Linux execution, not a claim that remote Ubuntu CI ran. Remote CI remains unexecuted
until a future authorized push or manual workflow execution.

The original six tests pass on both platforms, including byte-level source snapshot
hashes, the ordered historical 59-feature schema, model hyperparameters, submission
identities, and historical manifests. `legacy_amazon/**` and `archive_manifest/**`
have zero changes. No private historical pipeline rerun was performed.

## Limitations and claim boundary

- PUBLIC_PASS applies to the new C1/C2 contracts and P0 retrieval behavior. Private
  Amazon parity, leaderboard outcomes, WDC quality, and historical-scale resources
  have not been newly reproduced.
- Private historical capped-sample membership and exact historical-scale candidate
  graphs are unverified. Historical RNG positions alone do not establish membership
  parity across canonical and historical materialization orders.
- Historical evidence remains historical. The preserved leaderboard value and
  cross-script feature experiment are not new Pass A measurements.
- The implementation holds entities and the bounded candidate union in memory.
  Sparse products are bounded; million-record memory/throughput is unmeasured.
- Country equality defines eligibility, including null-to-null. Cross-country truths
  require a separately declared adapter/policy; they are rejected by this baseline.
- S2/S3 ID collisions require an external reversible adapter because the frozen pair
  contract omits target source from its key. IDs are never inferred from prefixes.
- Top-N cutoff ties are deterministic on canonical input with the pinned sparse
  library, without claiming a globally lexical tie-selection policy.
- Recall@K is per forward lane and an explicitly named union, not a model/global
  ranking. Reverse query Recall@K and empty-truth recall are undefined.
- OS memory counters may differ transiently; frontier RSS includes earlier points in
  the same process. No isolated stage-memory or statistically robust timing claim.
- Binary run artifacts, plots, temporary scripts, caches, and virtual environments
  remain local and ignored; the committed 568,496-byte evidence file is metadata,
  not a generated dataset. Exact versions, hashes, warnings, and source identities
  are retained there. Reproduction regenerates the bulk artifacts.
- No private data, credentials, secrets, model weights, or large generated datasets
  are added. Historical source and Unicode text remain unchanged.

## Exact remaining C3 prerequisites

Pass A provides entities, normalization, splits, candidate provenance, public truth
fixtures, manifests, and lineage. C3 implementation remains wholly outstanding:

1. Implement the ordered historical 59-feature reference engine and immutable
   schema/order/hash contract, with float32 batch conversion and public function-parity
   fixtures. Exact private probabilities remain optional private evidence.
2. Freeze retrieval-derived negative mining and labelled split/no-leakage policy.
3. Introduce separate FeatureRow, ScoredCandidate, OwnershipResult,
   CandidateDisposition, and ResolutionDecision contracts; stage fields must not merge.
4. Implement the thin scorer interface and LightGBM reference training/config identity,
   then scoring quality and calibration reports.
5. Implement global target ownership with `score DESC, s1_id ASC`, one owner per
   target, and rival diagnostics, independently of decoding.
6. Implement the historical `is_owner and score >= 0.640` decoder and zero/one/many
   resolution sets, keeping rejected candidate dispositions.
7. Implement set-level macro F0.5/precision/recall/exact-set evaluation and public
   end-to-end invariants for exclusivity and threshold adherence.
8. Implement deterministic earliest-policy-stage attribution using the v1.1
   RETRIEVAL / SCORING / OWNERSHIP / DECODING precedence and genuine label ambiguity.
9. Implement Resolution Evidence Capsules with raw signals and explicit undefined
   values; no pre-decided stability label.
10. Add the gated train/resolve/evaluate CLI surfaces, public synthetic C3 acceptance,
    and any separately authorized private parity run. C4 challengers, research,
    benchmarks, and release remain deferred.

No C3 action was taken as part of this change.
