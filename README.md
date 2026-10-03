# Concord

Concord resolves noisy multilingual business records into zero, one or many target
matches, with reproducible evidence for retrieval, scoring and each final decision.
It is an individual project architected, implemented, tested and documented by
**Adithya Sanjeevi**. Concord evolved from earlier Amazon ML Challenge 2026
entity-resolution work; the challenge submission's historical provenance is
preserved separately.

Entity resolution is difficult because names and addresses vary across languages,
scripts, punctuation and missing fields. Similar names can describe different
businesses, several target records can represent the same business, and competing
source records can claim the same target. Comparing every possible pair also becomes
impractical as the target universe grows.

## Architecture

```text
Validated records + deterministic normalization
  → bounded five-view sparse retrieval
  → ordered 59-feature reference engine
  → LightGBM scoring
  → global target ownership: score DESC, s1_id ASC
  → fixed decoder: owner AND score ≥ 0.640
  → zero / one / many matches + compact evidence + evaluation
```

The retrieval views cover name, compact name, address, combined name/address and
reverse combined retrieval. Features consume only the bounded candidate graph.
Scoring, ownership, dispositions and resolution sets have separate immutable
contracts. Typed Parquet stores bulk products; canonical JSON records configurations,
reports, artifact hashes and parent identities. Failure attribution identifies
policy stages, while evidence capsules retain raw diagnostics with undefined values
represented explicitly.

## Public reproduction

Requires Python 3.12 or later. New Concord code runs on native Windows and Linux.

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/reproduce_pass_a.py --output outputs/pass-a-demo
python scripts/reproduce_pass_b.py --output outputs/pass-b-demo
```

Pass A covers contracts, normalization, identities and bounded retrieval. Pass B
adds features, retrieval-derived hard negatives, training, calibration, resolution,
set evaluation and evidence using invented, entity-disjoint train/calibration/test
splits. The current CLI exposes `inspect`, `retrieve`, `train`, `resolve` and
`evaluate` with gated subcommands.

Pass B recorded **189 passing tests on each of native Windows and Ubuntu/WSL**.
Clean reproductions retained 18 completed manifests per platform; logical scores,
resolution sets and evaluation reports matched for the synthetic fixture. Its test
macro set F0.5 was **0.6145833333333334**, including intentional failure cases.
These observations describe the fixture, not general model or benchmark performance.

See [Pass A usage](docs/PASS_A_USAGE.md), [Pass B usage](docs/PASS_B_USAGE.md),
[Pass A evidence](PASS_A_EVIDENCE.md), [Pass B evidence](PASS_B_EVIDENCE.md) and the
[C3 closure audit](docs/audit/C3_CLOSURE_AUDIT.md). The
[Windows/Ubuntu CI workflow](.github/workflows/public-verification.yml) configures
tests and both reproductions; configured CI is not evidence of remote execution.

## Preserved historical baseline

The earlier challenge pipeline resolved **1.73M source entities against a 9.97M
target universe using bounded multi-view retrieval that produced an 87.9M-pair
candidate graph**. The graph was a bounded subset of possible comparisons.

| Item | Verified value |
|---|---:|
| Public leaderboard Macro F0.5 | 0.955136 |
| POLICY_DEV Macro F0.5 | 0.9593640004712406 |
| Test Source-1 rows | 1,732,544 |
| Valid Source-2/Source-3 target IDs | 9,969,589 |
| Frozen candidate pairs | 87,934,151 |
| Accepted links | 5,708,382 |
| Empty Source-1 output rows | 100,939 |

These are historical observations supported by preserved artifacts and submission
chronology, not newly reproduced C3 results or current live leaderboard verification.
[Results](docs/RESULTS.md), [Provenance](docs/PROVENANCE.md) and the
[experiment ledger](docs/EXPERIMENT_LEDGER.md) describe their evidence and limits.

`src/concord/legacy_amazon/` remains frozen historical authority, including the
ordered schema and model configuration. `archive_manifest/` preserves original
source, artifact and experiment identities. Historical replay requires privately
supplied organizer data/model files and high-memory Linux or WSL2; see
[Reproducibility](docs/REPRODUCIBILITY.md). New implementation lives outside that
legacy boundary.

## Claim and redistribution boundaries

Git excludes private organizer data, model weights, generated candidate/feature
tables, submission outputs, caches and environments. Public function/schema tests
do not establish private feature, model, probability or capped-sampling parity.
No WDC performance, historical-scale throughput, leaderboard improvement or
stability finding is claimed. C4 research and release work remain deferred.

No open-source license is attached. Challenge-derived code and artifact
redistribution terms require review; absence of a license grants no additional
permission beyond applicable rights.
