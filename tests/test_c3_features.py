import ast
import re
import sqlite3
import time
import unicodedata
from dataclasses import FrozenInstanceError, asdict, replace
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import unidecode
from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler

from concord.c3_contracts import FEATURE_VERSION, FeatureRow
from concord.contracts import EntityRecord, LaneEvidence, RetrievalCandidate
from concord.features.reference import (
    FEATURE_NAMES,
    REFERENCE_SCHEMA,
    context_features,
    cross_features,
    direct_features,
    feature_matrix,
    generate_features,
)
from concord.metadata import content_sha256, read_json
from concord.normalization import normalize, normalize_text
from concord.retrieval.baseline import RetrievalConfig, retrieve, synthetic_config, vectorizer

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "src/concord/reference_baseline"


def reference(path, names, namespace):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(selected, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


@pytest.fixture
def reference_feature_functions():
    namespace = {"re": re, "np": np, "pd": pd, "pa": pa, "pq": pq, "time": time, "Path": Path,
                 "WORD": re.compile(r"\w+", re.UNICODE), "NUM": re.compile(r"\d+"),
                 "fuzz": fuzz, "JaroWinkler": JaroWinkler, "BASE_FEATURES": list(FEATURE_NAMES[:38])}
    return reference(REFERENCE / "features.py",
                     {"direct", "rep", "tri", "overlap", "coord", "_worker", "_context_sql"}, namespace)


@pytest.mark.parametrize("values", [
    ("Exact Invented Shop", "12 Fable Road", "Exact Invented Shop", "12 Fable Road"),
    ("Invented Blue Shop", "12 12 8 Avenue", "Blue Trading Shop", "12 8 9 Avenue"),
    (None, "12 Fable Road", "Target Name", "12 Fable Road"),
    ("", "", "", ""), ("Query", None, "Target", ""),
    ("Query", "", "Target", None), ("Café ﬁ Ａ", "18 Allée", "Cafe fi A", "18 Allee"),
    ("A.C.M.E. & Co!", "#12/8-B", "ACME", "12 8 B"),
    ("Ακμή", "23 Οδός", "Akmi", "23 Odos"),
    ("कमल दुकान", "१२ सड़क", "Kamal Dukan", "12 Road"),
    ("東京商店", "18 Main", "Tokyo", "18 Main"),
])
def test_reference_direct_and_cross_function_parity(values, reference_feature_functions):
    qn, qa, tn, ta = values
    adapted = tuple(normalize_text(v) or "" for v in values)
    for source in ("S2", "S3"):
        expected = reference_feature_functions["direct"](*adapted, source)
        assert np.array_equal(np.array(direct_features(*adapted, source), dtype=np.float32),
                              np.array(expected, dtype=np.float32))
    namespace = reference(REFERENCE / "crossscript.py",
                          {"get_script", "tri", "toks", "jaccard", "compute_4_features"},
                          {"re": re, "unicodedata": unicodedata, "np": np, "fuzz": fuzz, "unidecode": unidecode})
    frame = pd.DataFrame({"s1_id": ["opaque q"], "target_id": ["opaque t"]})
    qmap = {"opaque q": {"business_name": qn, "business_address": qa}}
    tmap = {"opaque t": {"business_name": tn, "business_address": ta}}
    actual = namespace["compute_4_features"](frame, qmap, tmap)
    assert np.array_equal(np.array(cross_features(*values), dtype=np.float32), np.array(actual).ravel())


def test_order_schema_identity_and_immutable_values():
    original = read_json(REFERENCE / "artifacts/ordered_59_feature_schema.json")
    assert tuple(original["ordered_features"]) == FEATURE_NAMES
    assert len(FEATURE_NAMES) == 59
    assert REFERENCE_SCHEMA.sha256 == content_sha256(asdict(REFERENCE_SCHEMA))
    ordered = REFERENCE_SCHEMA.ordered_features
    for replacement in ((ordered[1], ordered[0], *ordered[2:]),
                        (replace(ordered[0], name="changed"), *ordered[1:]),
                        (replace(ordered[0], definition_version="v2"), *ordered[1:]),
                        (replace(ordered[0], definition="different computation"), *ordered[1:])):
        assert replace(REFERENCE_SCHEMA, ordered_features=replacement).sha256 != REFERENCE_SCHEMA.sha256
    row = FeatureRow("q", "t", (0.,) * 59, FEATURE_VERSION, REFERENCE_SCHEMA.sha256)
    with pytest.raises(FrozenInstanceError):
        row.values = (1.,) * 59
    with pytest.raises(TypeError):
        row.values[0] = 1.
    assert feature_matrix((row,)).dtype == np.float32
    with pytest.raises(ValueError, match="schema mismatch"):
        feature_matrix((replace(row, schema_sha256="0" * 64),))
    for values in ([0.] * 59, (0.,) * 58, (float("nan"),) + (0.,) * 58, (float("inf"),) * 59):
        with pytest.raises(ValueError):
            replace(row, values=values)
    with pytest.warns(RuntimeWarning, match="overflow"), pytest.raises(ValueError, match="overflow"):
        feature_matrix((replace(row, values=(1e100,) + (0.,) * 58),))


def test_all_59_against_reference_worker_and_sql_on_uncapped_public_fixture(
        reference_feature_functions, tmp_path):
    """Actual worker + actual SQL expressions (SQLite window dialect adapter).

    Private sample ordering/model probabilities are not part of this claim.
    The reference SQL's FLOAT casts are applied at the final float32 boundary.
    """
    records = tuple(EntityRecord(f"q{i:04d}", "S1", f"Invented Lantern {i:04d}", f"{i} Fable Lot", "PUBLIC") for i in range(200)) + tuple(
        EntityRecord(f"t{i:04d}", "S2", f"Invented Lantern {i:04d}", f"{i} Fable Lot", "PUBLIC") for i in range(200))
    normalized = tuple(normalize(r) for r in records)
    config = RetrievalConfig()
    candidates = retrieve(normalized, config).candidates
    rows = generate_features(normalized, candidates, config)
    q, t = normalized[:200], normalized[200:]
    matrices = []
    for view in ("name", "compact", "address"):
        def text(r, view=view):
            s = r.business_address_normalized if view == "address" else r.business_name_normalized
            return s.replace(" ", "") if view == "compact" else s
        qa, ta = [text(r) for r in q], [text(r) for r in t]
        v = vectorizer(view, config).fit(qa + ta)
        matrices.extend((v.transform(qa).astype(np.float32), v.transform(ta).astype(np.float32)))
    graph_rows = []
    for c in candidates:
        ranks = {e.lane: e.rank - 1 for e in c.lane_evidence}
        graph_rows.append({"s1_id": c.s1_id, "target_id": c.target_id, "source": c.target_source,
                           "country": c.country, "retrieval_view_mask": c.retrieval_view_mask,
                           **{col: ranks.get(lane, 999) for lane, col in zip(
                               ("name", "compact", "address", "combined", "reverse"), FEATURE_NAMES[33:38], strict=True)}})
    graph = tmp_path / "reference-graph.parquet"
    pq.write_table(pa.Table.from_pylist(graph_rows), graph)
    ref_functions = reference_feature_functions
    ref_functions["_G"] = {"graph": str(graph), "q": [{"name": r.business_name_normalized, "address": r.business_address_normalized} for r in q],
                    "t": [{"name": r.business_name_normalized, "address": r.business_address_normalized} for r in t],
                    "qmap": {r.entity_id: i for i, r in enumerate(q)}, "tmap": {r.entity_id: i for i, r in enumerate(t)},
                    **dict(zip(("Qn", "Tn", "Qc", "Tc", "Qa", "Ta"), matrices, strict=True))}
    base = tmp_path / "reference-base.parquet"
    ref_functions["_worker"](("PUBLIC", 0, str(base)))
    frame = pq.read_table(base).to_pandas()
    sql = ref_functions["_context_sql"]("PUBLIC", "unused", "unused")
    query = sql[len("COPY ("):sql.index(") TO '")].replace("read_parquet('unused')", "base_input").replace("::FLOAT", "")
    with sqlite3.connect(":memory:") as con:
        frame.to_sql("base_input", con, index=False)
        expected = pd.read_sql_query(query, con)
    rawq = {r.entity_id: {"business_name": r.business_name, "business_address": r.business_address} for r in records[:200]}
    rawt = {r.entity_id: {"business_name": r.business_name, "business_address": r.business_address} for r in records[200:]}
    qualifier = reference(REFERENCE / "crossscript.py",
                          {"get_script", "tri", "toks", "jaccard", "compute_4_features"},
                          {"re": re, "unicodedata": unicodedata, "np": np, "fuzz": fuzz, "unidecode": unidecode})
    for name, column in zip(FEATURE_NAMES[-4:], qualifier["compute_4_features"](expected, rawq, rawt), strict=True):
        expected[name] = column
    assert np.array_equal(feature_matrix(rows), expected[list(FEATURE_NAMES)].to_numpy(dtype=np.float32))
    assert len(rows) == len(candidates)  # no Cartesian expansion


def test_sql_context_ties_and_source_groups(reference_feature_functions):
    candidates = tuple(RetrievalCandidate(q, t, source, None, 1, (LaneEvidence("name", 1, .5),))
                       for q, t, source in (("a", "t", "S2"), ("b", "t", "S2"), ("a", "u", "S3"), ("a", "v", "S2")))
    cosines = {("a", "t"): (.7, 0., .3, .5), ("b", "t"): (.7, 0., .2, .45),
               ("a", "u"): (.1, 0., .1, .1), ("a", "v"): (.2, 0., .4, .3)}
    result = context_features(candidates, cosines)
    assert result["a", "t"][0] == result["b", "t"][2] == 1.
    assert result["a", "t"][4] == 0.  # tied best is not a positive rival margin
    assert result["a", "u"][0] == 1.  # source partition separate
    assert result["a", "t"][-2:] == (2., 2.)


def test_missing_empty_and_absent_lane_numeric_adapter():
    records = (EntityRecord("q", "S1", None, "", None), EntityRecord("t", "S2", "", None, None))
    candidate = RetrievalCandidate("q", "t", "S2", None, 4, (LaneEvidence("address", 2, .1),))
    rows = generate_features(tuple(normalize(r) for r in records), (candidate,), synthetic_config())
    assert rows[0].values[24:28] == (1., 1., 1., 1.)
    assert rows[0].values[29:33] == (0., 0., 0., 0.)
    assert rows[0].values[33:38] == (999., 999., 1., 999., 999.)
    assert candidate.lane_evidence == (LaneEvidence("address", 2, .1),)
    assert records[0].business_name is None and records[1].business_name == ""


def test_feature_input_rejects_unknown_or_duplicate_graph(public_fixture):
    records, _ = public_fixture
    normalized = tuple(normalize(r) for r in records)
    candidates = retrieve(normalized, synthetic_config()).candidates
    with pytest.raises(ValueError, match="duplicate"):
        generate_features(normalized, candidates + (candidates[0],), synthetic_config())
    with pytest.raises(ValueError, match="supplied"):
        generate_features(normalized, (replace(candidates[0], target_id="unknown"),), synthetic_config())
