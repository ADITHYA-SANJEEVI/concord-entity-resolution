# Pass C public research reproduction

Pass C is a bounded P0 research layer over C1-C3. It changes no reference features,
ownership rule or 0.640 decoder threshold. Experiments are diagnostic only.

From the repository root with Python 3.12 and installed `.[dev]` dependencies:

```bash
python scripts/reproduce_pass_c.py --output outputs/pass-c-demo
```

The script runs two CLI commands, retains stdout/stderr and verifies every recorded
artifact's physical hash and size. It refuses to overwrite prior runs. The default
scale sizes are 128, 512 and 2048 source queries, with one warmup and three measured
repetitions **per size**. For a smaller integration check:

```bash
python scripts/reproduce_pass_c.py --output outputs/pass-c-small --sizes 16,32 --repetitions 2
```

The equivalent separate commands are:

```bash
concord benchmark public --output outputs/c4-public --population P0/multilingual-c4/public --track SYNTHETIC_PUBLIC --run-id c4-public
concord benchmark scale --model-run outputs/c4-public --output outputs/c4-scale --population P0/multilingual-c4/scale --track SYNTHETIC_PUBLIC --run-id c4-scale
```

`public` names the public reproducible suite; it does not imply a downloaded WDC
benchmark. Only the explicitly invented recipe `concord.p0.multilingual-c4.v1` is
supported. The committed split plan has 320 training, 64 calibration and 133 test
queries. All entity identities are disjoint between roles. Generator templates
are shared, so this is an integration/diagnostic experiment, not independent evidence
of real-world generalization. `P0-OOD` is an invented held-out country label.

The suite retrains the fixed LightGBM reference, logistic regression, six group
ablations, K=1, no reverse view, a bounded transliterated-name retrieval challenger,
and logistic seed 7. Group ablations zero the named C3 columns at training and
scoring without changing their order/schema. Logistic uses a training-only
StandardScaler, C=1, liblinear, tolerance 1e-8 and 2000 iteration limit. All experiments
retain the same decoder. No calibration/test labels enter fitting or graph generation.

The zero-based C3 column groups are:

| Ablation | Columns zeroed |
|---|---|
| Name | 0-9, 24-25, 29-30 |
| Address | 10-17, 26-27, 31 |
| Numeric address tokens | 18-23 |
| Retrieval | 32-37 (combined cosine and five ranks) |
| Competition | 38-54 (graph ranks, deltas, margins and counts) |
| Cross-script | 55-58 |

Column 28 (S2 indicator) stays present. These are group ablations, not mutually
exclusive causal interventions: retained graph/cross-script signals can contain
information related to a removed direct group.

Transliteration retrieval unions the historical five views with a separate top-five
name view of Unidecode-transformed raw names. On overlap the original C2 record wins;
rescued rows carry the actual transformed name-lane evidence, with origin metadata.
The original-record 59 features are then computed on that bounded union. This is an
explicit new retrieval identity, never the historical baseline.

Case, spacing, punctuation, token order, transliteration and added competition
perturb only S1 inputs. Each reruns retrieval, features, scoring, ownership, decoding
and evidence with the frozen fitted reference. Changes use the original 133-query
denominator; competition adds a query which also enters its full quality report.
Row permutation and repeated training/inference are executed separately. Evidence
capsules contain raw diagnostics and no stability label.

The predeclared structural risk score combines lane count, ownership margin,
threshold margin and ambiguity. Undefined accepted diagnostics contribute zero
before inversion. The main confidence baseline uses one minus minimum accepted
score; a zero-match uses top rejected score, or zero for no candidates. Four
individual confidence baselines and zero/nonempty populations are also measured.
Query bootstrap intervals are descriptive: shared targets/templates violate a
simple independent real-world sampling interpretation. Undefined AUROC/AUPRC are null.

Scale uses the already fitted reference. Stage timers cover normalization, retrieval,
features, scoring, ownership, decoding and evidence; total pipeline includes sampler
bookkeeping. Imports, fixture generation, model loading, garbage collection and
serialization are excluded. RSS is sampled with psutil every 10 ms plus stage
start/end, consistently on Windows and Linux. Reported maxima are sampled process
RSS, include dependencies and retained allocator state, and can miss short spikes.
They are neither isolated stage allocations nor OS high-water marks. Repetitions
share a process; platform timings are not controlled hardware comparisons.

Bulk observations, all evaluated pipeline stages and every Failure Atlas entry are
typed Parquet. Canonical JSON metadata/capsules/reports use existing manifests and
artifact DAG validation. Atlas evidence keeps top-eight candidates plus the
attributed pair if retrieved; the complete graph and stages are separately retained.
Attribution is the earliest C3 policy gate, not causal root-cause analysis. Zero
observed stage counts are retained rather than filled with simulated failures.

Outputs remain ignored. Git retains code, the explicit split plan, and the compact
evidence bundle/report. Models, candidate tables, logs and environments are not staged.
Clean evidence identifies its producing implementation commit and source hashes;
an evidence-only commit subsequently retains the report without self-reference.

After clean Windows and Ubuntu reproductions, verify both and generate the compact
bundle from their physically retained artifacts:

```bash
python scripts/retain_pass_c_evidence.py --windows outputs/pass-c-windows-clean --linux outputs/pass-c-linux-clean --output docs/evidence/PASS_C_RUNS.json
```

This checks the combined public/scale DAG, producing source bytes, clean Git state,
exact resolution/quality/logical failure attribution and changed query sets. It
records actual score deltas and a diagnostic 1e-12 comparison flag without imposing
probability equality. Raw failure score/margin diagnostics are retained independently.
Model text, numeric probabilities and timings are not required to match. Models and
Parquet remain in the ignored run directories.

WDC, Ditto, Splink, adaptive K and semantic matching are outside this completed suite.
There is no frontend, inspection API, C5, release/tag or automatic model promotion.
