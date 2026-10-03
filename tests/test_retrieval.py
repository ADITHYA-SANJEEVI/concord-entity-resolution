import time
from dataclasses import FrozenInstanceError, asdict, replace

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import scipy.sparse as sp
from sparse_dot_topn import sp_matmul_topn

from concord.contracts import LANES, EntityRecord, LaneEvidence, RetrievalCandidate
from concord.normalization import normalize
from concord.retrieval.analysis import candidate_fingerprint, evaluate_retrieval, frontier
from concord.retrieval.baseline import (
    CANONICAL_SAMPLING_ORDER,
    EMPTY_VOCABULARY_POLICY,
    REFERENCE_K,
    RetrievalConfig,
    _fit_sample_positions,
    materialize_views,
    retrieve,
    synthetic_config,
    union_candidates,
    vectorizer,
)
from concord.storage import CANDIDATE_SCHEMA, read_candidates, write_candidates


@pytest.mark.parametrize("name,address,compact,missing", [
    (None, None, "", (True, True)), ("", "", "", (False, False)),
    (" A\t B\n ", " 18 Main Rd. ", "a\tb\n", (False, False)),
])
def test_view_boundary(name, address, compact, missing):
    normalized = normalize(EntityRecord("x", "S1", name, address))
    views = materialize_views(normalized)
    assert views.compact == compact
    assert (views.name_missing, views.address_missing) == missing
    assert views.combined_name == views.name
    assert views.combined_address == views.address
    with pytest.raises(FrozenInstanceError):
        views.name = "changed"


@pytest.mark.parametrize("view", ["name", "compact", "address"])
def test_reference_vectorizer_parity(view, reference_functions):
    assert vectorizer(view, RetrievalConfig()).get_params() == reference_functions["vec"](
        view).get_params()


@pytest.mark.parametrize("bad", [
    {"budgets": [5, 5, 5, 10, 8]}, {"budgets": (0, 5, 5, 10, 8)},
    {"budgets": (1,) * 5}, {"lanes": ("name",)}, {"min_df": 1}, {"max_df": 1.0},
    {"seed": 42}, {"threads": 0}, {"profile": "transliteration"}, {"max_df": float("nan")},
])
def test_frozen_baseline_config(bad):
    with pytest.raises(ValueError):
        RetrievalConfig(**bad)


@pytest.mark.parametrize("lane,rank,score", [("unknown", 1, .5), ("name", 0, .5),
                                          ("name", True, .5), ("name", 1, float("nan")),
                                          ("name", 1, 0), ("name", 1, 2)])
def test_invalid_evidence(lane, rank, score):
    with pytest.raises(ValueError):
        LaneEvidence(lane, rank, score)


def test_immutable_union_mask_and_conflicts():
    a = RetrievalCandidate("query", "target", "S3", None, 1, (LaneEvidence("name", 1, .5),))
    b = replace(a, retrieval_view_mask=16, lane_evidence=(LaneEvidence("reverse", 2, .25),))
    c, = union_candidates((b, a))
    assert c.retrieval_view_mask == 17 and c.contributing_lane_count == 2
    assert c.available_without("name") and c.available_without("reverse")
    assert a.available_without("name") is False
    assert union_candidates((a, b)) == (c,)
    with pytest.raises(ValueError):
        replace(a, lane_evidence=list(a.lane_evidence))
    with pytest.raises(ValueError):
        replace(a, retrieval_view_mask=2)
    with pytest.raises(ValueError):
        replace(c, lane_evidence=tuple(reversed(c.lane_evidence)))
    with pytest.raises(ValueError):
        union_candidates((a, a))
    with pytest.raises(ValueError):
        union_candidates((a, replace(b, target_source="S2")))
    with pytest.raises(FrozenInstanceError):
        c.lane_evidence[0].similarity = .1


def test_deterministic_bounded_retrieval(public_fixture):
    records, truth = public_fixture
    normalized = tuple(normalize(r) for r in records)
    config = synthetic_config(chunk_size=2)
    a = retrieve(normalized, config)
    b = retrieve(tuple(reversed(normalized)), replace(config, chunk_size=3))
    assert a.candidates == b.candidates
    assert candidate_fingerprint(a.candidates) == candidate_fingerprint(b.candidates)
    assert a.fit_evidence == b.fit_evidence
    assert len(a.candidates) <= min(a.eligible_cartesian_pairs, a.candidate_pair_bound)
    report = evaluate_retrieval(records, a.candidates, truth)
    assert report["truth_pairs"] == len(truth)
    assert report["truths_recovered"] <= len(truth)
    assert report["zero_candidate_queries"] >= 1
    assert len(a.candidates) == len({(c.s1_id, c.target_id) for c in a.candidates})
    for lane, k in zip(LANES, config.budgets, strict=True):
        degree = {}
        for c in a.candidates:
            for e in c.lane_evidence:
                if e.lane == lane:
                    assert 1 <= e.rank <= k
                    key = c.target_id if lane == "reverse" else c.s1_id
                    degree[key] = degree.get(key, 0) + 1
        assert all(n <= k for n in degree.values())
    assert report["eligible_cartesian_pairs"] == a.eligible_cartesian_pairs
    assert report["truth_pair_recall"] == report["truths_recovered"] / len(truth)
    for lane in LANES:
        ablation = report["leave_one_lane_out_candidate_availability"][lane]
        rescue = report["lane_rescue"][lane]
        assert ablation["truths_lost"] == rescue["unique_truths_rescued"]


def test_reverse_bounds_are_per_target():
    rows = (EntityRecord("q", "S1", "Identical Brand", "18 Main Road"),) + tuple(
        EntityRecord(f"t{i:03d}", "S2", "Identical Brand", "18 Main Road") for i in range(40))
    run = retrieve(tuple(normalize(r) for r in rows), synthetic_config())
    assert len(run.candidates) == 40
    assert len(run.candidates) > sum(REFERENCE_K[:-1])
    assert all(any(e.lane == "reverse" for e in c.lane_evidence) for c in run.candidates)


def test_no_vocabulary_no_fallback(public_fixture):
    rows, truth = public_fixture
    run = retrieve(tuple(normalize(r) for r in rows))
    assert run.candidates == ()
    assert run.warnings
    assert evaluate_retrieval(rows, run.candidates, truth)["truth_pair_recall"] == 0


@pytest.mark.parametrize("rows", [(), (EntityRecord("q", "S1", None, ""),),
                                 (EntityRecord("t", "S3", "Brand", "Road"),)])
def test_empty_universe(rows):
    run = retrieve(tuple(normalize(r) for r in rows), synthetic_config())
    assert not run.candidates
    report = evaluate_retrieval(rows, run.candidates)
    assert report["reduction_ratio"] is None
    assert report["truth_pair_recall"] is None
    assert report["truths_recovered"] is None


def test_duplicate_and_ambiguous_ids():
    a = normalize(EntityRecord("x", "S2", "Brand", "Road"))
    for rows in ((a, a), (a, replace(a, source="S3"))):
        with pytest.raises(ValueError):
            retrieve(rows, synthetic_config())


def test_candidate_parquet_nulls(public_fixture, tmp_path):
    records, _ = public_fixture
    candidates = retrieve(tuple(normalize(r) for r in records), synthetic_config()).candidates
    path = tmp_path / "candidates.parquet"
    write_candidates(path, candidates)
    assert read_candidates(path) == candidates
    table = pq.read_table(path)
    assert table.schema.equals(CANDIDATE_SCHEMA, check_metadata=True)
    assert any(table[f"{lane}_rank"].null_count > 0 for lane in LANES)
    row = table.to_pylist()[0]
    row["name_rank"], row["name_similarity"] = 1, None
    pq.write_table(pa.Table.from_pylist([row], schema=CANDIDATE_SCHEMA), path)
    with pytest.raises(ValueError):
        read_candidates(path)
    write_candidates(path, ())
    assert read_candidates(path) == ()


def test_metric_denominators_and_lane_rescue():
    rows = tuple(EntityRecord(q, "S1", q, None) for q in ("q1", "q2", "q0")) + tuple(
        EntityRecord(t, "S2", t, None) for t in ("t1", "t2", "t3"))
    a = RetrievalCandidate("q1", "t1", "S2", None, 1, (LaneEvidence("name", 1, .9),))
    b = RetrievalCandidate("q1", "t2", "S2", None, 17,
                           (LaneEvidence("name", 2, .8), LaneEvidence("reverse", 1, .8)))
    c = RetrievalCandidate("q2", "t3", "S2", None, 4, (LaneEvidence("address", 1, .7),))
    truth = (("q1", "t1"), ("q1", "t2"), ("q2", "t2"))
    report = evaluate_retrieval(rows, (a, b, c), truth)
    assert report["truth_pair_recall"] == 2 / 3
    assert report["recall_at_k_by_forward_lane"]["name"]["1"] == 1 / 3
    assert report["recall_at_k_by_forward_lane"]["name"]["5"] == 2 / 3
    assert report["reduction_ratio"] == 1 - 3 / 9
    assert report["zero_candidate_rate"] == 1 / 3
    assert report["density"]["mean"] == 1
    assert report["lane_rescue"]["name"]["unique_truths_rescued"] == 1
    assert report["leave_one_lane_out_candidate_availability"]["name"]["candidate_pairs"] == 2
    assert report["lane_overlap_truths"]["name"]["reverse"] == 1
    assert report["truths_by_lane_count"]["1"] == 1
    assert report["truths_by_lane_count"]["2"] == 1
    assert evaluate_retrieval(rows, (a, b, c), ())["truth_pair_recall"] is None
    for bad in ((truth[0], truth[0]), (("unknown", "t1"),), (("q1", "unknown"),)):
        with pytest.raises(ValueError):
            evaluate_retrieval(rows, (a, b, c), bad)
    with pytest.raises(ValueError):
        evaluate_retrieval(rows, (a, a), truth)
    with pytest.raises(ValueError):
        evaluate_retrieval(rows, (replace(a, country="US"),), truth)


def test_frontier_pareto_and_no_promotion(public_fixture):
    rows, truth = public_fixture
    normalized = tuple(normalize(r) for r in rows)
    run = retrieve(normalized, synthetic_config(budgets=(1,) * 5))
    slower = replace(run, wall_seconds=run.wall_seconds + 10,
                     sampled_peak_rss_bytes=run.sampled_peak_rss_bytes + 100)
    report = frontier(rows, (run, slower), truth)
    first, second = report["points"]
    assert first["pareto_candidate_pairs"] and second["pareto_candidate_pairs"]
    assert first["pareto_wall_seconds"] and not second["pareto_wall_seconds"]
    assert first["pareto_sampled_peak_rss_bytes"] and not second["pareto_sampled_peak_rss_bytes"]
    assert report["promotion"] == "DIAGNOSTIC_ONLY"


def test_reference_sparse_retrieve_rank_adapter(reference_functions, tmp_path):
    """Reference bounded products and ranks agree on a no-tie public numeric fixture.

    Reference ranks are zero-based; the new boundary intentionally adds one.
    """
    class Volume:
        def commit(self):
            pass

    reference_functions.update({"OUT": tmp_path, "CHUNK": 2,
                                 "K": dict(zip(LANES, REFERENCE_K, strict=True)),
                                 "sp_matmul_topn": sp_matmul_topn, "pd": pd, "time": time})
    q = [{"s1_id": f"q{i}"} for i in range(3)]
    t = [{"target_id": f"t{i}"} for i in range(4)]
    qm = sp.csr_matrix(np.array([[.9, .1], [.1, .8], [.4, .6]], dtype=np.float32))
    tm = sp.csr_matrix(np.array([[1, 0], [0, 1], [.3, .7], [.7, .3]], dtype=np.float32))
    for lane in LANES:
        left, right = (tm, qm) if lane == "reverse" else (qm, tm)
        reference_functions["retrieve"](lane, q, t, left, right, "public", Volume())
        reference = pd.concat(pd.read_parquet(p) for p in
                               sorted((tmp_path / "checkpoints/public" / lane).glob("*.parquet")))
        expected = left @ right.T  # only the tiny test oracle may use an unrestricted product
        actual = {}
        for _, row in reference.iterrows():
            key = row.s1_id, row.target_id
            actual[key] = int(row[f"{lane}_rank"]) + 1
            qi, ti = int(row.s1_id[1:]), int(row.target_id[1:])
            i, j = (ti, qi) if lane == "reverse" else (qi, ti)
            column = "combined" if lane == "reverse" else lane
            assert row[f"{column}_cosine"] == pytest.approx(expected[i, j])
        for i in range(left.shape[0]):
            order = sorted(range(right.shape[0]), key=lambda j: -expected[i, j])
            for rank, j in enumerate(order[:REFERENCE_K[LANES.index(lane)]], 1):
                key = (q[j]["s1_id"], t[i]["target_id"]) if lane == "reverse" else (
                    q[i]["s1_id"], t[j]["target_id"])
                assert actual[key] == rank


def test_reference_uncapped_reference_graph_parity(reference_functions):
    """Function/reference parity only; this population never reaches FIT_CAP."""
    # 200 pairs keep each unique full-name/address term below reference max_df.
    rows = []
    for i in range(200):
        name = f"brand{i:04x}"
        address = f"location{i:04x}"
        rows += [EntityRecord(f"q{i:03d}", "S1", name, address, "US"),
                 EntityRecord(f"t{i:03d}", "S2", name, address, "US")]
    config = RetrievalConfig()
    run = retrieve(tuple(normalize(r) for r in rows), config)
    qrows, trows = rows[::2], rows[1::2]
    matrices = {}
    for lane in LANES[:3]:
        qtext = [r.business_address if lane == "address" else r.business_name for r in qrows]
        ttext = [r.business_address if lane == "address" else r.business_name for r in trows]
        v = reference_functions["vec"](lane)
        try:
            v.fit(qtext + ttext)
        except ValueError:
            matrices[lane] = (sp.csr_matrix((200, 0), dtype=np.float32),) * 2
        else:
            matrices[lane] = v.transform(qtext), v.transform(ttext)
    weight = np.float32(np.sqrt(.5))
    matrices["combined"] = tuple(sp.hstack([
        matrices["name"][i].multiply(weight), matrices["address"][i].multiply(weight),
    ]).tocsr() for i in (0, 1))
    expected = {}
    for lane in LANES:
        qm, tm = matrices["combined" if lane == "reverse" else lane]
        left, right = (tm, qm) if lane == "reverse" else (qm, tm)
        if not left.shape[1]:
            continue
        hits = sp_matmul_topn(left, right.T.tocsr(), top_n=REFERENCE_K[LANES.index(lane)],
                             threshold=0.0, sort=True, n_threads=1).tocoo()
        for i, j, value in zip(hits.row, hits.col, hits.data, strict=True):
            pair = (qrows[j].entity_id, trows[i].entity_id) if lane == "reverse" else (
                qrows[i].entity_id, trows[j].entity_id)
            expected[pair, lane] = float(value)
    actual = {(c.s1_id, c.target_id, e.lane): e.similarity
              for c in run.candidates for e in c.lane_evidence}
    assert actual == {(q, t, lane): value for ((q, t), lane), value in expected.items()}
    assert run.candidates


def test_fit_sampling_repeatable(public_fixture):
    rows, _ = public_fixture
    normalized = tuple(normalize(r) for r in rows)
    config = synthetic_config(fit_cap=4)
    a, b = retrieve(normalized, config), retrieve(tuple(reversed(normalized)), config)
    assert a.fit_evidence == b.fit_evidence and a.candidates == b.candidates
    assert all(e.sample_count <= 4 for e in a.fit_evidence)
    assert all(type(v) not in (dict, list) for v in asdict(config).values())
    with pytest.raises(ValueError):
        replace(a, candidates=list(a.candidates))
    # Linux getrusage and psutil/statm use separate OS accounting snapshots.
    # Preserve both observed counters; neither is fabricated to order them.
    assert a.peak_process_rss_bytes > 0 and a.sampled_peak_rss_bytes > 0


@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_actual_fit_cap_position_boundary(offset):
    """Exercise the real 3M cutoff using positions only, without private records."""
    config = RetrievalConfig()
    population = config.fit_cap + offset
    selected = _fit_sample_positions(population, config)
    assert len(selected) == min(population, config.fit_cap)
    assert np.all(np.diff(selected) > 0)
    assert selected[0] >= 0 and selected[-1] < population
    if offset <= 0:
        assert np.array_equal(selected, np.arange(population))


@pytest.mark.parametrize("population", [3, 4, 5])
def test_capped_membership_order_boundary_against_reference_sampler(
        population, reference_functions, tmp_path):
    """Public reduced-cap experiment on the reference sampler, not private parity.

    Equal seeded positions imply equal membership only if materialization order
    matches (or all records are selected). Capture the actual reference sample file.
    The vectorizer stub isolates membership from vocabulary fitting.
    """
    class Volume:
        def commit(self):
            pass

    class CaptureVectorizer:
        vocabulary_ = {"public": 0}

        def fit(self, text):
            return self

        def transform(self, text):
            return sp.csr_matrix(np.ones((len(text), 1), dtype=np.float32))

    q = [{"s1_id": key, "name": f"brand {key}", "address": "18 Main Road"}
         for key in ("q-z", "q-a")]
    t = [{"target_id": key, "name": f"brand {key}", "address": "18 Main Road"}
         for key in ("t-z", "t-y", "t-x")[:population - len(q)]]
    reference_functions.update({
        "OUT": tmp_path, "MOUNT": tmp_path, "SEED": 0, "FIT_CAP": 4,
        "vec": lambda view: CaptureVectorizer(),
    })
    reference_functions["fit_transform"](q, t, "name", "public", Volume())
    sample = (tmp_path / "vectorizer_samples/public_name.txt").read_text().splitlines()
    original_ids = ["q:" + row["s1_id"] for row in q] + ["t:" + row["target_id"] for row in t]
    reference_positions = [original_ids.index(key) for key in sample]
    rows = tuple(EntityRecord(row["s1_id"], "S1", row["name"], row["address"], "public")
                 for row in q) + tuple(
        EntityRecord(row["target_id"], "S2", row["name"], row["address"], "public") for row in t)
    config = synthetic_config(fit_cap=4)
    selected = _fit_sample_positions(population, config)
    assert reference_positions == selected.tolist()
    canonical = sorted(rows, key=lambda row: (row.source, row.entity_id))
    canonical_sample = [canonical[int(i)] for i in selected]
    reference_members = {key[2:] for key in sample}
    canonical_members = {row.entity_id for row in canonical_sample}
    if population > config.fit_cap:
        assert reference_members != canonical_members
    else:
        assert reference_members == canonical_members
    run = retrieve(tuple(normalize(row) for row in rows), config)
    for evidence in run.fit_evidence:
        assert evidence.population_count == population
        assert evidence.cap_applied is (population > config.fit_cap)
        assert evidence.sampling_order_policy == CANONICAL_SAMPLING_ORDER
        assert evidence.reference_capped_sample_parity == "UNVERIFIED"
        with pytest.raises(ValueError, match="has not been verified"):
            replace(evidence, reference_capped_sample_parity="VERIFIED")
        from concord.metadata import content_sha256

        assert evidence.sample_fingerprint == content_sha256([
            (row.source, row.entity_id) for row in canonical_sample])


def test_sampling_and_fail_safe_policies_fingerprinted_and_immutable():
    from concord.metadata import content_sha256

    config = RetrievalConfig()
    values = asdict(config)
    assert values["sampling_order_policy"] == CANONICAL_SAMPLING_ORDER
    assert values["empty_vocabulary_policy"] == EMPTY_VOCABULARY_POLICY
    values.pop("sampling_order_policy")
    assert config.fingerprint != content_sha256(values)
    with pytest.raises(FrozenInstanceError):
        config.sampling_order_policy = "reference-materialization"
    with pytest.raises(ValueError):
        replace(config, sampling_order_policy="reference-materialization")
    with pytest.raises(ValueError):
        replace(config, empty_vocabulary_policy="reference-raise")


def test_empty_vocabulary_is_new_fail_safe_not_reference_execution(reference_functions, tmp_path):
    class Volume:
        def commit(self):
            pass

    reference_functions.update({"OUT": tmp_path, "MOUNT": tmp_path,
                                 "SEED": 0, "FIT_CAP": 3_000_000})
    q = [{"s1_id": "q", "name": "", "address": ""}]
    t = [{"target_id": "t", "name": "", "address": ""}]
    with pytest.raises(ValueError):
        reference_functions["fit_transform"](q, t, "name", "public", Volume())
    run = retrieve((normalize(EntityRecord("q", "S1", "", "", "public")),
                    normalize(EntityRecord("t", "S2", "", "", "public"))))
    assert run.candidates == () and len(run.warnings) == 3
    assert run.config.empty_vocabulary_policy == EMPTY_VOCABULARY_POLICY
    assert all(e.vocabulary_size == 0 for e in run.fit_evidence)
