# Concord C3 targeted closure audit

**Status: PASS.** Starting checkpoint:
`ff7abafc0494cab53803d02beecc383df4128ccd`, clean tree on
`c3/scoring-resolution-evidence`. Implementation checkpoint:
`fd875dbd7e1a26ea1616f2b740a8c79b87d13e49`. Accepted Pass A checkpoint:
`70abb57241b246bec4fcee5b26e672735588e46f`.

This closure reviews existing C3 semantics and current public project attribution.
It does not begin C4 or generate a new benchmark. Concord is individually
architected, implemented, tested and documented by Adithya Sanjeevi. Earlier Amazon
ML Challenge 2026 work is separate historical provenance; this audit does not assign
sole authorship of the external submission.

## Semantic review

The review read the nine C3 implementation files, C3 tests, workflow, README,
[Pass B usage](../PASS_B_USAGE.md), [Pass B evidence](../../PASS_B_EVIDENCE.md),
architecture freeze, Amendment 001 and the authoritative v1.1 flagship, data,
experiment and implementation contracts. Amendment 001 supersedes older proposals.
No concrete C3 correctness defect was found. No executable source or test was changed.

| Stage | Code reviewed | Finding |
|---|---|---|
| Features | `features/reference.py`, `c3_contracts.py` | Exactly 59 ordered definitions. Immutable finite tuple boundary; ordered name/definition/version schema hash, independent of storage dtype. No feature-name sorting. Reference sparse cosines retain C2 float32 arithmetic; public values and Parquet are Python/float64 numbers, with the full matrix converted at the batch/model boundary. Numeric compatibility adapters remain confined to features. |
| Negatives/splits | `modeling/training.py`, `c3_cli.py` | Explicit committed entity-disjoint groups cover the dataset. CLI validates selected records and normalization against completed C2 artifacts. Mining uses retrieved train pairs only, deterministic similarity/hash selection and retained provenance. Held-out records and truth do not enter training; truth is consumed after retrieval. |
| Scoring | `modeling/scorer.py`, `c3_contracts.py` | Thin numeric scorer interface; no ownership or acceptance state in scores. Reference 600/.05/63/L2=1 configuration preserved. Seed 42 remains `DEFAULTED_TO_42_NO_PRIOR_VALUE_FOUND`, not original historical seed recovery. Model loading checks bytes, metadata, configuration, schema and feature order. |
| Ownership | `inference/resolution.py` | All competitors in the evaluated population are grouped by target and ordered score DESC, s1_id ASC. Exactly one rank-1 owner, independent of input order. Owner rival is runner-up; loser rival is winner; singleton diagnostics are None. |
| Decoder | `inference/resolution.py`, `c3_contracts.py` | Acceptance is exactly owner AND score >= 0.640. Separate immutable disposition; no threshold tuning or additional SET_POLICY exclusion. Forged rank/order combinations are rejected. |
| Resolution | `inference/resolution.py`, `c3_storage.py` | Every declared S1 receives sorted unique accepted IDs and zero/single/multi type. Zero-match is an empty tuple. Exclusive ownership prevents duplicate accepted targets across S1s. |
| Evaluation | `evaluation/quality.py`, `c3_cli.py` | Macro per-S1 set F0.5, precision, recall and exact-set accuracy are separate from retrieved-pair calibration. Empty-set conventions and truth-based cohorts are explicit. Held-out evaluation rejects train populations. |
| Attribution | `evaluation/failures.py`, `c3_cli.py` | For defensible labels, FN gates are retrieval absence, score inadmissibility, ownership loss, then decoding mis-emission. Genuine externally declared label conflicts are handled separately, not inferred from model error. Missing pipeline evidence raises errors. Admissible FP scores are SCORING; score-ineligible/out-of-graph emission is DECODING. This is policy-stage attribution, not causal proof. |
| Evidence/lineage | `inference/resolution.py`, `c3_storage.py`, `c3_cli.py` | Compact immutable capsules propagate dataset/split/retrieval/schema/model/decoder/code identities. Undefined diagnostics stay None; no is_stable field. Typed stages and hashed parent edges connect graph, features, mining/model, scores, ownership, dispositions, sets, evaluation and evidence. Consumed run artifacts are hash/size checked. |

The ordered C3 schema remains `concord.features.historical-59.v1`, SHA-256
`6450b326649beb45e9b9ac7d5a0617934a1c9b21c7ca1f5a12c8b9a3c92ba6f8`.
Public function/reference parity is unchanged; private parity remains unperformed.

## Public repository cleanup

Removed explicit former-member and collective authorship wording from current
README, package author metadata, origin, resume guidance and affected audit prose.
The package author is Adithya Sanjeevi alone. Current architecture/usage documents
and examples were scanned; documents with no attribution problem were left intact.
Historical experiment filenames remain lookup references, not authorship statements.

README now explains the ER problem, bounded retrieval through evidence architecture,
public C1-C3 reproduction, historical scale and claim boundaries. Its earlier archive
basename is replaced by links to provenance. Historical counts, scores, hashes and
experiment dispositions were not changed. Earlier proposal headers now explicitly
identify their superseding v1.1 contracts; their illustrative values are not presented
as measured runs or current contracts.

## Remaining legacy identifiers

These are the remaining name-like or tool-like historical tokens found across tracked
files. A display alias in new prose would be safe, but silently changing a frozen
identifier, manifest entry or historical source is not allowed in this closure.
No identity below is interpreted as current project authorship.

| Exact token(s) | Where / why retained | Rename classification |
|---|---|---|
| `asmi-crossscript-reproduced-59-v1` | Frozen ordered schema and older proposal examples referencing that schema. | Schema identity and physical source hash are preserved; not safely renameable in the frozen artifact. A neutral illustrative alias would be safe only outside the historical reference. |
| `asmi-crossscript-59-reproduced-v1` | Original output-directory reference in `archive_manifest/artifacts.json` and experiment ledger. | Frozen manifest/path provenance; no silent rename. |
| `asmi_crossscript_local_01`, `asmi_crossscript_test_production_01`, `asmi_crossscript_reproduction_01` | Frozen experiment-directory records and ledger lookup paths. | Referenced by historical manifests; no silent rename. |
| `asmi_modeling_transfer`, `asmi_snapshot_transfer` | Original directory names/paths in `archive_manifest/artifacts.json`. | Frozen historical provenance; no silent rename. |
| `ayan_retrieval_01`, `ayan_retrieval_light_01`, `ayan_retrieval_light_02`, `ayan_retrieval_full_01` | Frozen experiment records and ledger lookup paths. | Referenced by historical manifests; no silent rename. |
| `ayan_retrieval_01.py`, `ayan_retrieval_light_01.py` | Ledger filenames for original externally archived source. | Historical lookup filenames; prose aliases are safe, renaming the original reference would impair lookup. |
| `Aurorawave_submission.zip`, `aurorawave_submission.zip` | Original archive basename/case variants in frozen manifests and historical artifact lookup documentation. | The artifact bytes have a pinned SHA-256; a display alias does not change those bytes, but frozen manifest names remain unchanged. |
| `ASMI` | Original comment in `legacy_amazon/qualified_crossscript_generator.py`. | Frozen source bytes are hashed in `archive_manifest/source_snapshot.json`; comment editing would break the preservation contract. |
| `codex3_direct_0950_feature_challenger_01`, `codex4_india_oracle_rescue_01`, `codex5_embedding_interaction_verifier_01` | Frozen historical experiment records and ledger paths. | Tool-like opaque experiment IDs, referenced by manifests; no silent rename or current authorship claim. |
| `codex6_triadic_coherence_01`, `codex6_zero_match_abstention_01`, `codex6_top50_crossencoder_01` | Frozen historical experiment records and ledger paths. | Same manifest/provenance boundary. |
| `codex7_train_lookup_dictionary_01`, `codex7_expected_f05_decision_01`, `codex11_sequential_stopping_01` | Frozen historical experiment records and ledger paths. | Same manifest/provenance boundary. |
| Original `team`/`members` field values in `archive_manifest/final_submission.json` | Unmodified historical submission metadata, including the original `Aurorawave` label and former-member names. Those names are not repeated in current prose. | Explicitly protected historical manifest; not current attribution, and not safely editable under the zero-change boundary. |

Adithya Sanjeevi and owner-local path tokens are intentional current attribution.
The invented `Invented Aurora` test businesses are synthetic data, unrelated to
historical authorship; changing them would needlessly alter accepted fixtures.

## CI workflow review

Renamed `.github/workflows/pass-a.yml` to
`.github/workflows/public-verification.yml`. Its existing name already described
C1-C3, so the filename now reflects its actual scope. Contents and commands are
identical: Python 3.12, Windows/Ubuntu matrix, editable dev install, full pytest,
Ruff, compileall, diff check, both public scripts and retained output artifacts.
Historical evidence lists retain the old filename because they describe earlier
commits. No remote workflow execution is claimed; no push occurred.

## Closure validation

Only prose, author metadata and a workflow filename changed. Runtime dependencies,
C3 source, tests and synthetic inputs are identical to the starting checkpoint.
Accordingly, the expensive full cross-platform suites and fresh public pipeline
were not repeated. The earlier 189/189 full-suite passes and 36 clean manifests
remain prior Pass B evidence, not new closure measurements.

Executed on native Windows / Python 3.12.10:

```powershell
.venv\Scripts\python.exe -m pytest -q --tb=short tests/test_c3_features.py tests/test_c3_resolution.py tests/test_c3_training_storage.py tests/test_c3_cli.py tests/test_preserved_contract.py tests/test_manifests.py -k 'not complete_public_c3_cli_and_no_leakage and not manifests_physical_hashes_and_stage_lineage and not invalid_parent_hash_and_failed_c3_run_are_retained'
.venv\Scripts\python.exe -m ruff check src/concord --exclude legacy_amazon tests scripts examples/synthetic/pass_b_fixture.py
.venv\Scripts\python.exe -m compileall -q src/concord tests scripts examples/synthetic/pass_b_fixture.py
git diff --check
```

**83 passed, 0 failed, 0 skipped, 3 deselected in 6.14 seconds.** The three
deselected tests share the full public reproduction fixture. All other C3 cases and
the six original historical tests ran. Ruff and compileall passed. The existing
pytest-asyncio fixture-scope deprecation warning remained visible.

Focused repository validation checks current attribution, sole package author,
unchanged dependency/runtime configuration, README and modified-document links,
byte-equivalent workflow contents, exact staged scope, credentials/large-file
patterns and protected paths. It validates the retained 36 clean manifest instances,
their physical artifact/source hashes and eight actual capsules against the original
outputs. Closure does not relabel their producing commit or dirty state.

## Preservation and claim boundary

Zero changes to `src/concord/legacy_amazon/**`, `archive_manifest/**`,
`tests/test_preserved_contract.py` and `tests/test_manifests.py`. Accepted retrieval,
Pass A evidence and Pass B run metadata are unchanged; the Pass A tag is unchanged.
No private inputs, model binaries, generated bulk artifacts, environments, caches or
temporary scripts are committed. Commit identity remains the owner's configured Git
identity, with no additional authorship trailers.

Historical public F0.5 0.955136 remains historical. C3 metrics describe invented P0
fixtures only. No private parity, WDC quality, scale/production throughput, leaderboard
improvement, unrecovered result or stability/drift finding is promoted. C4 research,
benchmark and release prerequisites remain deferred. No C4 implementation, push,
merge or release/tag is part of this closure.
