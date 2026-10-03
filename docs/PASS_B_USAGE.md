# Concord Pass B: C3 usage and semantics

C3 adds features, reference scoring, global ownership, decoding, evaluation, stage
attribution and resolution evidence. C4 research builds on these same contracts.
All public reproduction inputs are invented synthetic records.

## Install and reproduce

```powershell
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe scripts/reproduce_pass_b.py --output outputs/pass-b-demo
```

Linux uses the equivalent environment's `python`. The script executes all C3 CLI
surfaces, repeats training and resolution, and retains canonical manifests, reports,
typed Parquet, model text and diagnostic logs under the ignored output directory.
Outputs must be new or empty; previous failures and evidence are retained.

The invented P0 fixture has committed entity-disjoint split membership in
`examples/synthetic/pass_b_splits.json`: 240 training queries / 480 targets,
12 calibration queries / 24 targets, and 16 test queries / 21 targets. No automatic
partitioning occurs. Calibration and test labels never enter training. Each split
gets its own C2 retrieval and feature-vectorizer population, so no held-out records
or graph-context values enter training either. The full logical dataset, split plan,
split membership and local split dataset identities are all recorded.

## CLI

Training consumes a validated completed C2 run matching the declared split:

```text
concord train negatives --entities all.parquet --split-plan splits.json --split train --retrieval-run retrieval-train --truth train-truth.json --output negatives --population P0/my-fixture/train --track SYNTHETIC_PUBLIC --run-id negatives-1
concord train fit --entities all.parquet --split-plan splits.json --split train --retrieval-run retrieval-train --truth train-truth.json --output model --population P0/my-fixture/train --track SYNTHETIC_PUBLIC --run-id fit-1
concord train fingerprint --model-run model
concord resolve run --entities all.parquet --split-plan splits.json --split test --retrieval-run retrieval-test --model-run model --output resolution --population P0/my-fixture/test --track SYNTHETIC_PUBLIC --run-id resolve-1
concord resolve explain --resolution-run resolution --s1-id opaque-query-id
concord resolve export-evidence --resolution-run resolution
concord evaluate quality --resolution-run resolution --truth test-truth.json --output quality --population P0/my-fixture/test --track SYNTHETIC_PUBLIC --run-id quality-1
```

`evaluate calibration|failures|policy` accepts the same evaluation arguments.
`train calibrate` is a descriptive held-out calibration report with those same
arguments; it does not fit a transform or tune the threshold. Every evaluation
surface retains quality, calibration, failure and frozen-policy reports, while
stdout selects the requested surface. C3 stdout is canonical machine-readable JSON;
LightGBM diagnostics remain on stderr and in reproduction logs.

Training optionally accepts `--negative-config` and `--model-config` JSON for the
validated immutable configurations. Model reference hyperparameters remain frozen.
An evaluation command rejects training populations. Unknown or cross-split labels,
entity/normalization mismatch, invalid feature schema, changed parent artifacts,
wrong model identity, and inconsistent policy outputs are rejected.

No unfinished replay, benchmark, drift, stability or retrieval-challenger command is
exposed. Re-executing the public script is the bounded C3 reproduction path.

## Features and parity boundary

The ordered reference has exactly 59 definitions: 29 direct string/numeric/source
features, four exact sparse cosines, five reference numeric lane ranks, 17 graph-context
features, and four reference cross-script features. The immutable schema hashes
the ordered names, definitions and definition versions, including its schema version.
Dtype is not part of this schema identity. Public `FeatureRow.values` is a tuple of
finite numbers; storage preserves float64 values, and conversion to float32 happens
at the batch/model boundary. Overflow at that boundary is rejected.

The engine consumes C2 candidates and computes coordinate-only sparse dot products
for those pairs. It never generates candidates or computes an all-pairs score matrix.
Exact name/compact/address cosines are available even when a lane did not retrieve
the pair. Their vectorizers use the declared C2 parameters and canonical fit policy.
The combined exact feature is float32 `0.5*name + 0.5*address`, as in the reference
worker. Graph-context SQL RANK semantics preserve ties and source partitions; these
pre-model similarity ranks are features, not final ownership results.

Two explicit numeric compatibility adapters preserve reference feature definitions:

- Missing and empty normalized text both produce the reference empty-input numeric
  features. Raw and normalized entity records retain `None` versus `""` unchanged.
- A present C2 one-based lane rank becomes a zero-based numeric model feature;
  absent ranks become the reference numeric feature value `999`. This value is confined
  to the reference feature vector. C2 lane provenance stays absent/null, and contains
  no sentinel.

Public tests execute reference direct and four-feature functions on exact, partial,
missing/empty, Unicode, punctuation, numeric, acronym-like and cross-script fixtures.
A full 59-column test executes the reference worker and reference SQL expressions
on an uncapped public graph, with a documented SQLite window-dialect adapter, then
compares at the reference float32 boundary. Reference SQL's `::FLOAT` cast is
applied at that final numeric boundary; window expressions are unchanged.

These are public function/schema/reference claims. They are not private feature-
value or probability parity. Private capped sample membership and reference-scale
full-graph parity remain UNVERIFIED, as documented in Pass A. Feature transliteration
implements the reference four features only; retrieval gains are not claimed.

## Negative mining and scorer

`concord.top-retrieval-hard-negatives.v1` keeps all retrieved training truths and up
to 16 non-truth retrieved pairs per query, ordered by maximum lane similarity
descending. A seed-42 content hash breaks selection ties reproducibly. This seed is
a new explicit mining configuration, not a claim about original reference mining.
Unknown/cross-split pairs are rejected. Unretrieved truths are counted but never
injected into the graph. Each mined pair records label, selection reason, graph,
retrieval configuration, split and mining identities. Closed-world labels are
assumed within each declared split; incomplete labels would invalidate mining.

The scorer interface is `fit`, `predict_proba`, `get_params`, `fingerprint`. It sees
numeric matrices and emits probabilities; it knows nothing about retrieval,
ownership, decoding or attribution. The LightGBM reference config uses 600 trees,
learning rate 0.05, 63 leaves, min_child_samples 100, L2 1.0, subsample/column sample
1.0, no class weights and no early stopping. Seed 42 is declared by
`concord.fixed-seed-42.v1`. Single threading, deterministic mode and column-wise
fitting are explicit portability settings.
Actual fitted tree count is recorded, not inferred from the requested count.

Model identity includes format, actual artifact hash, config, ordered feature schema,
training dataset/split/plan, mining configuration and sampled-pair identity, feature
artifact, retrieval configuration, LightGBM/NumPy versions and actual tree count.
Local paths are not model identity. Loading validates model bytes, metadata identity,
library version, config and feature order. Repeat checks are within a platform;
cross-platform binary-model equality is not assumed.

## Ownership, decoder and sets

Ownership is global across all competing S1s in the declared candidate population,
with `score DESC, s1_id ASC`. One rank-1 owner exists per target. Its rival is the
runner-up; a loser's rival is the winner. Margin is candidate score minus rival score;
it is undefined for a singleton competitor set. No Python iteration order enters
arbitration.

The reference decoder accepts exactly `is_owner and score >= 0.640`. The rejection
reason is BELOW_THRESHOLD first when score-ineligible, otherwise LOST_OWNERSHIP.
Accepted candidates use NONE. SET_POLICY remains reserved and is never fabricated
by this baseline. All rejected rows remain in typed disposition artifacts.

Every evaluated S1 gets a decision with sorted unique accepted IDs: empty tuple,
single target or multiple targets. A target cannot appear in two accepted sets.
Scores, ownership, disposition and resolution are separate immutable types.

## Evaluation and attribution

Macro metrics average per-S1 sets, including zero-match queries. Empty truth and
empty prediction have P=R=F0.5=1. Empty truth with nonempty prediction has P=F0.5=0,
R=1. Nonempty truth with empty prediction has P=R=F0.5=0. Exact-set accuracy compares
sets. Empty cohorts/populations have undefined averages (`None`). Truth-based
zero/single/multi cohorts report their query counts.

Pair AUROC, AUPRC, log loss, Brier score, fixed reliability bins, ECE and score
distributions describe retrieved held-out pairs only. Missing-class AUROC/AUPRC and
empty-population metrics are undefined. Slope/intercept are not estimated. The small
fixture cannot establish general calibration or model quality; pair AUROC is not
end-to-end resolution quality. No held-out labels tune parameters or threshold.

False-negative precedence is retrieval absence, then score below 0.640, then lost
ownership, then an admissible owner not emitted. DECODING can identify a mis-emitted
artifact; this baseline implements no additional set exclusion. False positives
with admissible scores are principally SCORING; score-ineligible/out-of-graph emission
is DECODING. Ownership and rejection context remain diagnostics. Missing pipeline
artifacts raise an error rather than becoming an ambiguity label.

`--ambiguities` optionally names `[s1_id,target_id,reason]` annotations for genuine
label/data conflicts. The public fixture explicitly labels one target for two S1s
despite exclusive ownership, and declares that conflict. It is not inferred from
low scores or ordinary model errors. Attribution is deterministic policy-stage
attribution, not causal proof. C3 emits raw counts/examples, not the C4 Failure Atlas.

## Resolution evidence and lineage

Capsules retain accepted sets, candidate counts, top score, minimum accepted lane
count, alternate-lane availability, minimum ownership/threshold margins and ambiguity
ratio, plus dataset/split/retrieval/schema/model/decoder/code identities. Ambiguity
ratio is second-best candidate score divided by best score when both exist and best
is positive; otherwise it is `None`. Accepted margins/lane diagnostics are `None`
for zero-match decisions. Minimum ownership margin is undefined when any accepted
target has no rival. No `is_stable`, counterfactual stability or robustness label is
computed. Explain adds at most five top rejected candidates with their actual lane,
ownership and disposition records.

Bulk features, mined pairs, scores, ownership, dispositions, resolutions and
attribution use strict versioned Parquet. Canonical JSON stores metadata, manifests,
schema, reports and compact evidence. Each artifact records parent content/config
identities, producing configuration and commit, stage/schema and class D. External
parent hashes connect training and resolution/evaluation runs. Physical file hashes
and logical dataset/prediction/resolution identities remain distinct.

FAILED manifests use the validated Pass A failure writer and retain the original
exception. Run timers describe stage execution after parent/input verification,
including artifact generation, not complete CLI startup. RSS is process-wide, not
isolated stage memory. All resource observations are tiny-fixture smoke measurements.
