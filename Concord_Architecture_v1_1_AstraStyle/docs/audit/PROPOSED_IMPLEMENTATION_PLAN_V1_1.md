# Proposed Implementation Plan v1.1 — Concord Flagship

**Status:** AUTHORITATIVE GATED PLAN AFTER ARCHITECTURE AMENDMENT 001

---

## Gate C1 — Foundation, contracts, provenance

### Build
- corrected immutable data contracts;
- explicit `None` vs `""`;
- versioned historical-compatible normalization;
- logical dataset fingerprint;
- split fingerprint;
- canonical JSON serializer;
- Parquet entity/normalized-entity IO;
- artifact-parent lineage record;
- manifest instance validator + separate JSON Schema;
- `concord inspect profile|schema|fingerprint`;
- Windows + Ubuntu/Linux CI matrix.

### Tests
- non-null parity against historical `fold()`;
- composed/decomposed Unicode;
- null/empty distinction;
- opaque IDs;
- country optionality;
- row-order-independent fingerprint;
- duplicate identity rejection;
- Parquet round trip;
- canonical JSON;
- Windows local;
- Linux CI/WSL;
- historical six tests unchanged.

### Exit
`PUBLIC_PASS` achieved. No C2 code exists.

---

## Gate C2 — Retrieval, provenance, public retrieval benchmark

### Build
- five historical retrieval views as frozen baseline;
- immutable lane evidence;
- bounded candidate union;
- `retrieval_view_mask`;
- candidate-count distributions;
- truth recall / Recall@K;
- Reduction Ratio;
- lane-rescue matrix;
- leave-one-lane-out candidate-availability analysis;
- retrieval Pareto frontier;
- `concord retrieve run|frontier|lane-rescue|ablate`;
- WDC Products adapter/config if practical.

### Challengers
- transliteration retrieval challenger may be implemented but never silently promoted.

### Exit
- bounded graph;
- no Cartesian fallback;
- provenance on 100% candidates;
- public retrieval report;
- fixed baseline + challenger clearly separated.

---

## Gate C3 — Features, scoring, ownership, decoding, evidence

### Build
- 59-feature historical reference engine;
- immutable feature schema identity;
- retrieval-derived negatives;
- thin scorer interface;
- LightGBM reference;
- calibration report;
- distinct ScoredCandidate / OwnershipResult / CandidateDisposition types;
- global ownership;
- `0.640` historical baseline policy;
- macro F0.5;
- stage attribution;
- Resolution Evidence Capsule;
- `concord train`;
- `concord resolve run|explain|export-evidence`;
- `concord evaluate quality|calibration|failures|policy`.

### Public acceptance
- schema/function parity on public/reference fixtures;
- end-to-end synthetic pipeline;
- no duplicate target owner;
- deterministic manifest.

### Private parity
Optional:
- full probability/output parity only when authorized private data/model artifacts exist.

---

## Gate C4 — Cross-script research, stability, drift, benchmarks, release

### Build/Run
- SAME_SCRIPT/CROSS_SCRIPT cohorts;
- OOD/country cohorts;
- WDC public quality matrix;
- cross-script retrieval challenger;
- optional adaptive-K challenger;
- failure atlas;
- drift lens;
- S1 stability-vs-confidence experiment;
- benchmark smoke/public/scale;
- exact hardware/resource metadata;
- self-contained evidence report from manifests;
- `concord benchmark`;
- remaining evaluate sub-surfaces.

### Statistics
- bootstrap confidence intervals;
- no "confirmed null" from p>0.05;
- no invented benchmark numbers;
- null/negative challenger results retained.

### Exit
- release reproducible without private Amazon data;
- historical/private evidence clearly separated;
- claim boundary audited;
- all benchmark claims resolve to manifests/artifact hashes.

---

## Global stop rules

Stop and request an architecture amendment if implementation would:

- change historical retrieval semantics rather than add a challenger;
- alter ownership tie-breaking;
- change `0.640` as the historical baseline;
- merge scoring/ownership/decoder contracts;
- collapse null and empty;
- introduce private data into Git;
- add distributed infrastructure;
- add a semantic/LLM/vector system without a benchmarked need;
- claim a result before a manifest exists.
