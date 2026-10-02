# Reproducibility Audit: Concord Preserved Baseline

**Repository:** `concord-entity-resolution`  
**Preserved Baseline Commit:** `1133bfda496e2be59623fe154ec3dac45c13361f`  
**Preserved Baseline Tag:** `amazon-ml-2026-final`

---

## 1. Executive Summary

This reproducibility audit evaluates the exact conditions required to execute, verify, or retrain the preserved `amazon-ml-2026-final` baseline, and defines the cross-platform engineering requirements for new Concord development.

While contract and manifest validation tests are **Runnable Now** in any Python 3.12 environment, end-to-end execution of the historical competition pipeline is **blocked by two intentional omissions**:
1. Private organizer datasets (~2.52 GB).
2. Trained model weights (`cross_script_59_reproduced_model.joblib` [1.9 MB] and `.txt` [4.2 MB]).

Furthermore, the historical feature generation stage requires **Linux or WSL2** due to hard dependencies on Python's `fork` multiprocessing start method.

---

## 2. Stage-by-Stage Runnability Classification

| Pipeline Stage / Component | Runnability Classification | Blocking Dependencies / Constraints | Remediation / Verification Path |
|---|---|---|---|
| **Base Package Setup** | **RUNNABLE NOW** | None. `pyproject.toml` installs with `pip install -e .` | Python 3.12+ stdlib + hatchling. |
| **Preserved Contract Tests** | **RUNNABLE NOW** | Requires editable package installation (`pip install -e .`) | Run `pytest tests/ -v`. Verifies schemas, hashes, manifests, and pinned constants. |
| **Output Validation Utility** | **RUNNABLE NOW** | None (`src/concord/legacy_amazon/validate_submission.py` is stdlib-only). | Runnable on any TSV outputs with `--test-dir`. |
| **Output Comparison Utility** | **RUNNABLE NOW** | None (`src/concord/legacy_amazon/compare_outputs.py` is stdlib-only). | Streams and hashes pairs of TSVs with semantic equality checking. |
| **Deterministic Normalization** | **RUNNABLE NOW** | None (`fold()` uses `unicodedata`). | Verified self-contained Unicode NFKD + casefold function. |
| **Cross-Script 4-Feature Generator** | **RUNNABLE AFTER DEPENDENCY REPAIR** | Requires `rapidfuzz`, `unidecode`, `numpy` (`pip install -e ".[amazon]"`). | Standalone feature generator; runnable on arbitrary string pairs. |
| **TF-IDF Multi-View Retrieval** | **RUNNABLE ONLY WITH PRIVATE DATA** | Requires private `train_source*.tsv` or `test_source*.tsv`, plus `sparse-dot-topn`. | Bounded sparse matrix multiplication requires raw query/target inputs. |
| **55-Feature Generation** | **RUNNABLE ONLY WITH PRIVATE DATA + LINUX** | Requires private candidate graph, high memory (~128 GB recommended), and Linux/WSL2 `fork`. | Hard failure on Windows native: `get_context("fork")` raises `ValueError`. |
| **LightGBM Model Scoring** | **RUNNABLE ONLY WITH OMITTED MODEL + DATA** | Requires private candidate graph and omitted model weights (`.joblib` / `.txt`). | Checksums of omitted models pinned in `archive_manifest/artifacts.json`. |
| **Global Target Ownership** | **RUNNABLE NOW (LOGIC) / DATA REQUIRED** | Requires scored candidate table; DuckDB SQL engine is cross-platform. | Self-contained SQL window query partition logic. |
| **Submission Packaging / Hash Check** | **RUNNABLE NOW** | Requires generated outputs to match against pinned hashes. | Verifies against `AMAZON_SUBMISSION_SHA256`. |

---

## 3. Analysis of Historical Environment Gaps

Inspection of `src/concord/legacy_amazon/` revealed several historical shortcuts and operational constraints:

### 3.1 The Linux `fork` Multiprocessing Dependency
In `src/concord/legacy_amazon/frozen_stage1_55_scorer.py` (lines 149-152):
```python
with get_context("fork").Pool(min(WORKERS, os.cpu_count() or WORKERS)) as pool:
    rows = list(pool.imap_unordered(_worker, remaining, chunksize=1))
```
- **Issue:** On Windows, `get_context("fork")` is unavailable (Windows only supports `spawn`). Running this code on native Windows crashes immediately.
- **Historical Rationale:** `fork` allowed worker processes to inherit massive in-memory sparse TF-IDF matrices (`_G["Qn"]`, `_G["Tn"]`, etc.) via copy-on-write without serialization overhead.

### 3.2 Mutable Global State (`_G`)
In `frozen_stage1_55_scorer.py` (lines 53, 147):
```python
_G = {}
# ...
_G.update(q=q, t=t, qmap=qmap, tmap=tmap, Qn=Qn, Tn=Tn, Qc=Qc, Tc=Tc, Qa=Qa, Ta=Ta, graph=str(graph))
```
- **Issue:** Relying on module-level globals across workers breaks clean library encapsulation and prevents thread-based execution.

### 3.3 Hardcoded Infrastructure Paths
The historical source contains literal path constants tied to specific execution environments:
- `/volume` and `/volume/input`, `/volume/output` (Modal cloud volume mount points)
- `/root/validate_submission.py` (Hardcoded in `frozen_test_production.py:650`)
- `C:\Users\adith\Downloads\6ab10eb3b23ba_student_resource` (Local workstation paths in manifests)

### 3.4 Seed Recovery State
In `src/concord/legacy_amazon/artifacts/lightgbm_config.json`:
```json
{
  "random_state": 42,
  "seed_recovery": "DEFAULTED_TO_42_NO_PRIOR_VALUE_FOUND"
}
```
- While the refit model achieved decision parity and near-zero probability error ($\le 1.97 \times 10^{-11}$), the original training run seed was lost and re-established at 42.

---

## 4. Omitted Artifacts & Rights Boundary

The repository intentionally excludes large binary files. These exclusions are documented with cryptographic fingerprints in `archive_manifest/artifacts.json`:

```text
cross_script_59_reproduced_model.joblib
SHA-256: c5b0e2246794f5e79d6cfed1e16d82040d682bdee4cf94eccb760d61e69d6610 (1,924,340 bytes)

cross_script_59_reproduced_model.txt
SHA-256: 7c1797a78d4585647c818868a1d8960790cd2a5f77b9c90a36af9a2a4c710784 (4,236,607 bytes)

matching_results.tsv
SHA-256: 0153c2ad53f0cfbecce5339075968588d131d3144f6c85c49bb2a5a05741d145 (96,006,728 bytes)

candidate_pairs.tsv
SHA-256: 709164321b318e89763b37277dbcb2e96e40ccdcec93091bfe96c01a6e30a526 (1,155,697,650 bytes)

Aurorawave_submission.zip
SHA-256: d0574aab454f2e4798986ed5b488411bd04937b27ac6a9c17601235d4f07618e (523,531,529 bytes)
```

**Rights Rationale:** The challenge rules and terms under which the training data was distributed do not explicitly grant public redistribution rights for derived model weights or full entity sets. Retaining source code and schemas in Git while excluding weights preserves scientific auditability without infringing data agreements.

---

## 5. Private Replay Procedure (Historical Pipeline)

To execute a full private replay of the historical baseline:
1. Provision a Linux or WSL2 machine with Python 3.12, at least 128 GB RAM, and $\ge 50$ GB of scratch SSD disk.
2. Clone repository and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[amazon,dev]"
   ```
3. Place verified private models under `src/concord/legacy_amazon/artifacts/`:
   - `cross_script_59_reproduced_model.joblib`
   - `cross_script_59_reproduced_model.txt`
4. Confirm hashes match `archive_manifest/artifacts.json`.
5. Execute the historical orchestrator:
   ```bash
   python -m concord.legacy_amazon.run_pipeline \
     --train /path/to/private/train \
     --test /path/to/private/test \
     --work-dir /scratch/concord-work \
     --output /scratch/concord-out \
     --workers 32
   ```
6. Verify byte and semantic parity against pinned output hashes using `compare_outputs.py`.

---

## 6. Architecture Requirements for New Concord Development

Under **Decision D2 (Platform)**, all new Concord code implemented outside `legacy_amazon` must satisfy strict cross-platform standards:

1. **Native Windows & Linux Support:** New modules must run out of the box on both Windows native and Linux environments.
2. **Zero `fork` Assumptions:** Multiprocessing must use `spawn` or avoid ad-hoc process pooling by leveraging native multi-threaded tabular engines (DuckDB, PyArrow, Scipy OpenMP).
3. **No Hardcoded Absolute Paths:** All paths must be configurable, parameterized via CLI or config files, and resolved relative to working roots using `pathlib.Path`.
4. **Dual-Track Data Strategy (Decision D1):** New development must never require private Amazon datasets to demonstrate end-to-end functionality. The clean pipeline must execute completely on committed synthetic fixtures (`examples/synthetic/`) and public benchmarks.
