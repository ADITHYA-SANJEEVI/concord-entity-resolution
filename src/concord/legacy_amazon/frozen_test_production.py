"""Frozen Stage-1 TEST production pipeline.

Reuses the qualified five-view retrieval, 55-feature LightGBM, global target
ownership, and 0.640/0.640 thresholds.  It never reads FINAL_HOLDOUT.
"""
from __future__ import annotations

import gc
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from multiprocessing import get_context
from pathlib import Path

import duckdb
import joblib
import numpy as np
import pandas as pd
import psutil
import pyarrow as pa
import pyarrow.parquet as pq
import scipy.sparse as sp


MOUNT = Path("/volume")
INPUT = MOUNT / "input"
ROOT = MOUNT / "test_production_stage1_55"
RETRIEVAL = ROOT / "retrieval"
STAGE1 = ROOT / "stage1"
OUTPUT = ROOT / "output"
FROZEN_STAGE1 = MOUNT / "scorer/stage1_55"
CODE = INPUT / "code"
TEST = INPUT / "test"
THRESHOLD = {"S2": 0.640, "S3": 0.640}
WORKERS = 32
EXPECTED = {
    "builder": "22d785154cc8b04fd7b0cd5014f0e137fbd16baabf9ad992bb0234d24ad59535",
    "scorer": "666addde303070df8b1816dab0af75e7b913a192270e8378f9c491f5fc4a6b85",
    "model": "256dfc40137a5a284722f2ebe3f2b3fb08d9c91317907905d536a26a643ba3c1",
    "feature_schema": "a9542480e8b0ba1e5e7f4bf2f1ce968cd0816216e9eb261eab3a8543a959d3b5",
}


def write_json(value, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")


def _json_default(value):
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def import_frozen():
    if str(CODE) not in sys.path:
        sys.path.insert(0, str(CODE))
    import frozen_full_graph_builder as retrieval
    import frozen_stage1_55_scorer as scorer

    return retrieval, scorer


def _load_country(source: int, country: str, fold):
    records = []
    path = TEST / f"test_source{source}.tsv"
    for chunk in pd.read_csv(
        path,
        sep="\t",
        usecols=["entity_id", "business_name", "business_address", "country"],
        chunksize=250_000,
        dtype=str,
        keep_default_na=False,
    ):
        frame = chunk[chunk.country.eq(country)]
        if frame.empty:
            continue
        frame = frame.assign(
            name=frame.business_name.map(fold),
            address=frame.business_address.map(fold),
        )
        if source == 1:
            frame = frame.rename(columns={"entity_id": "s1_id"})
            records.extend(frame[["s1_id", "country", "name", "address"]].to_dict("records"))
        else:
            frame = frame.rename(columns={"entity_id": "target_id"})
            records.extend(frame[["target_id", "country", "name", "address"]].to_dict("records"))
    return records


def preflight(volume):
    began = time.time()
    volume.reload()
    ROOT.mkdir(parents=True, exist_ok=True)
    test_files = [TEST / f"test_source{i}.tsv" for i in (1, 2, 3)]
    if not all(path.is_file() for path in test_files):
        raise RuntimeError("Authorized TEST source transfer is incomplete")
    hashes = {
        "builder": sha256(CODE / "frozen_full_graph_builder.py"),
        "scorer": sha256(CODE / "frozen_stage1_55_scorer.py"),
        "model": sha256(FROZEN_STAGE1 / "model.txt"),
        "feature_schema": sha256(FROZEN_STAGE1 / "feature_schema.json"),
        "production_config": sha256(INPUT / "manifests/production_frozen_config.json"),
        "critical_path": sha256(INPUT / "manifests/production_critical_path.json"),
        "production_source": sha256(Path(__file__)),
    }
    hash_pass = all(hashes[key] == EXPECTED[key] for key in EXPECTED)
    con = duckdb.connect()
    counts = {}
    expected_columns = ["entity_id", "business_name", "business_address", "country"]
    schema_pass = True
    id_prefix_pass = True
    for source, path in enumerate(test_files, 1):
        columns = list(pd.read_csv(path, sep="\t", nrows=0).columns)
        schema_pass &= columns == expected_columns
        frame = con.execute(
            f"SELECT country,count(*) AS n,count(DISTINCT entity_id) AS unique_n,"
            f"sum(CASE WHEN starts_with(entity_id,'S{source}-') THEN 0 ELSE 1 END) AS bad_prefix "
            f"FROM read_csv('{path}',delim='\\t',header=true,all_varchar=true) GROUP BY country ORDER BY country"
        ).fetchdf()
        counts[f"S{source}"] = {row.country: int(row.n) for row in frame.itertuples()}
        id_prefix_pass &= bool((frame.bad_prefix == 0).all() and (frame.n == frame.unique_n).all())
    con.close()
    countries = sorted(counts["S1"])
    country_alignment_pass = all(set(counts[f"S{i}"]) == set(countries) for i in (1, 2, 3))
    disk = shutil.disk_usage("/")
    result = {
        "status": "PASS" if all((hash_pass, schema_pass, id_prefix_pass, country_alignment_pass)) else "FAIL",
        "hashes": hashes,
        "hash_pass": hash_pass,
        "schema_pass": schema_pass,
        "id_prefix_and_uniqueness_pass": id_prefix_pass,
        "country_alignment_pass": country_alignment_pass,
        "countries": countries,
        "counts": counts,
        "test_s1": sum(counts["S1"].values()),
        "test_targets": sum(counts["S2"].values()) + sum(counts["S3"].values()),
        "disk_total_gb": disk.total / 2**30,
        "disk_available_gb": disk.free / 2**30,
        "test_accessed": True,
        "final_holdout_accessed": False,
        "seconds": time.time() - began,
    }
    write_json(result, ROOT / "preflight.json")
    volume.commit()
    if result["status"] != "PASS":
        raise RuntimeError(f"TEST production preflight failed: {result}")
    return result


def retrieve_country(country: str, volume):
    result_path = RETRIEVAL / f"generation_{country}.json"
    graph_path = RETRIEVAL / "candidate_graph" / f"{country}.parquet"
    if result_path.exists() and graph_path.exists():
        return json.loads(result_path.read_text(encoding="utf-8"))
    retrieval, _ = import_frozen()
    if sha256(Path(retrieval.__file__)) != EXPECTED["builder"]:
        raise RuntimeError("Frozen retrieval builder hash changed")
    retrieval.OUT = RETRIEVAL
    retrieval.MOUNT = MOUNT
    retrieval.INPUT = INPUT
    began = time.time()
    q = _load_country(1, country, retrieval.fold)
    t2 = _load_country(2, country, retrieval.fold)
    t3 = _load_country(3, country, retrieval.fold)
    targets = t2 + t3
    del t2, t3
    if not q or not targets:
        raise RuntimeError(f"Empty TEST country population: {country}")
    counts = {
        "S2": sum(row["target_id"].startswith("S2-") for row in targets),
        "S3": sum(row["target_id"].startswith("S3-") for row in targets),
    }
    load_seconds = time.time() - began
    Qn, Tn, mn = retrieval.fit_transform(q, targets, "name", country, volume)
    Qc, Tc, mc = retrieval.fit_transform(q, targets, "compact", country, volume)
    Qa, Ta, ma = retrieval.fit_transform(q, targets, "address", country, volume)
    Qx = sp.hstack([Qn.multiply(np.float32(np.sqrt(.5))), Qa.multiply(np.float32(np.sqrt(.5)))]).tocsr()
    Tx = sp.hstack([Tn.multiply(np.float32(np.sqrt(.5))), Ta.multiply(np.float32(np.sqrt(.5)))]).tocsr()
    zero_vectors = {
        "query": {
            "name": int((np.diff(Qn.indptr) == 0).sum()),
            "compact": int((np.diff(Qc.indptr) == 0).sum()),
            "address": int((np.diff(Qa.indptr) == 0).sum()),
            "combined": int((np.diff(Qx.indptr) == 0).sum()),
        },
        "target": {
            "name": int((np.diff(Tn.indptr) == 0).sum()),
            "compact": int((np.diff(Tc.indptr) == 0).sum()),
            "address": int((np.diff(Ta.indptr) == 0).sum()),
            "combined": int((np.diff(Tx.indptr) == 0).sum()),
        },
    }
    matrices_ready = time.time()
    stages = {}
    for view, left, right in (
        ("name", Qn, Tn),
        ("compact", Qc, Tc),
        ("address", Qa, Ta),
        ("combined", Qx, Tx),
        ("reverse", Tx, Qx),
    ):
        stages[view] = retrieval.retrieve(view, q, targets, left, right, country, volume)
    retrieval_seconds = time.time() - matrices_ready
    graph = retrieval.union_country(country, volume)
    con = duckdb.connect()
    stats = con.execute(
        f"WITH c AS (SELECT s1_id,count(*) n FROM read_parquet('{graph}') GROUP BY s1_id) "
        "SELECT count(*) represented_s1,sum(n) candidate_pairs,avg(n) mean_candidates,"
        "quantile_cont(n,.5) p50,quantile_cont(n,.9) p90,quantile_cont(n,.99) p99,max(n) max_candidates FROM c"
    ).fetchdf().iloc[0].to_dict()
    source_stats = con.execute(
        f"WITH c AS (SELECT s1_id,source,count(*) n FROM read_parquet('{graph}') GROUP BY s1_id,source) "
        "SELECT source,sum(n) candidate_pairs,avg(n) mean_candidates,quantile_cont(n,.5) p50,"
        "quantile_cont(n,.9) p90,quantile_cont(n,.99) p99,max(n) max_candidates FROM c GROUP BY source ORDER BY source"
    ).fetchdf().to_dict("records")
    con.close()
    zero_candidate_s1 = len(q) - int(stats["represented_s1"])
    result = {
        "country": country,
        "queries": len(q),
        "targets": len(targets),
        "target_sources": counts,
        "load_seconds": load_seconds,
        "vectorizer_seconds": matrices_ready - began - load_seconds,
        "retrieval_seconds": retrieval_seconds,
        "union_seconds": time.time() - matrices_ready - retrieval_seconds,
        "total_seconds": time.time() - began,
        "graph": str(graph.relative_to(MOUNT)),
        "graph_sha256": sha256(graph),
        "graph_bytes": graph.stat().st_size,
        "vectorizers": [mn, mc, ma],
        "zero_vectors": zero_vectors,
        "zero_candidate_s1": zero_candidate_s1,
        "zero_candidate_rate": zero_candidate_s1 / len(q),
        "candidate_distribution": stats,
        "candidate_distribution_by_source": source_stats,
        "stages": stages,
        "peak_rss_mib": psutil.Process().memory_info().rss / 2**20,
    }
    write_json(result, result_path)
    volume.commit()
    return result


def _fit_feature_matrices(country, q, targets, qmap, tmap, retrieval):
    result = []
    metadata = []
    for view in ("name", "compact", "address"):
        field = "name" if view in ("name", "compact") else "address"

        def value(row):
            text = row[field]
            return text.replace(" ", "") if view == "compact" else text

        sample_path = RETRIEVAL / "vectorizer_samples" / f"{country}_{view}.txt"
        sample_ids = sample_path.read_text(encoding="utf-8").splitlines()
        fit = []
        for sample_id in sample_ids:
            prefix, entity_id = sample_id[:2], sample_id[2:]
            fit.append(value(q[qmap[entity_id]]) if prefix == "q:" else value(targets[tmap[entity_id]]))
        vectorizer = retrieval.vec(view)
        vectorizer.fit(fit)
        Q = vectorizer.transform([value(row) for row in q]).astype(np.float32)
        T = vectorizer.transform([value(row) for row in targets]).astype(np.float32)
        result.extend([Q, T])
        metadata.append(
            {
                "view": view,
                "vocabulary": len(vectorizer.vocabulary_),
                "sample_sha256": sha256(sample_path),
                "query_shape": list(Q.shape),
                "target_shape": list(T.shape),
                "query_nnz": int(Q.nnz),
                "target_nnz": int(T.nnz),
            }
        )
        del fit, vectorizer
        gc.collect()
    return result, metadata


def feature_country(country: str, volume):
    result_path = STAGE1 / f"generation_{country}.json"
    full_path = STAGE1 / "full_features" / f"{country}.parquet"
    if result_path.exists() and full_path.exists():
        return json.loads(result_path.read_text(encoding="utf-8"))
    retrieval, scorer = import_frozen()
    if sha256(Path(scorer.__file__)) != EXPECTED["scorer"]:
        raise RuntimeError("Frozen Stage-1 scorer source hash changed")
    began = time.time()
    q = _load_country(1, country, retrieval.fold)
    targets = _load_country(2, country, retrieval.fold) + _load_country(3, country, retrieval.fold)
    qmap = {row["s1_id"]: i for i, row in enumerate(q)}
    tmap = {row["target_id"]: i for i, row in enumerate(targets)}
    mats, vector_meta = _fit_feature_matrices(country, q, targets, qmap, tmap, retrieval)
    Qn, Tn, Qc, Tc, Qa, Ta = mats
    graph = RETRIEVAL / "candidate_graph" / f"{country}.parquet"
    base = STAGE1 / "base_features" / country
    base.mkdir(parents=True, exist_ok=True)
    scorer._G.clear()
    scorer._G.update(
        q=q,
        t=targets,
        qmap=qmap,
        tmap=tmap,
        Qn=Qn,
        Tn=Tn,
        Qc=Qc,
        Tc=Tc,
        Qa=Qa,
        Ta=Ta,
        graph=str(graph),
    )
    pf = pq.ParquetFile(graph)
    tasks = [(country, i, str(base / f"part_{i:05d}.parquet")) for i in range(pf.num_row_groups)]
    direct_started = time.time()
    with get_context("fork").Pool(min(WORKERS, os.cpu_count() or WORKERS)) as pool:
        parts = list(pool.imap_unordered(scorer._worker, tasks, chunksize=1))
    volume.commit()
    direct_seconds = time.time() - direct_started
    full_path.parent.mkdir(parents=True, exist_ok=True)
    context_started = time.time()
    if not full_path.exists():
        con = duckdb.connect()
        con.execute("PRAGMA threads=32")
        con.execute("PRAGMA memory_limit='96GB'")
        con.execute(f"PRAGMA temp_directory='/tmp/duckdb_{country}'")
        con.execute(scorer._context_sql(country, str(base / "*.parquet"), str(full_path)))
        con.close()
        volume.commit()
    context_seconds = time.time() - context_started
    con = duckdb.connect()
    invalid_terms = [f"sum(CASE WHEN {name} IS NULL OR NOT isfinite({name}) THEN 1 ELSE 0 END) AS \"{name}\"" for name in scorer.FEATURES]
    invalid = con.execute(f"SELECT {','.join(invalid_terms)} FROM read_parquet('{full_path}')").fetchdf().iloc[0].to_dict()
    con.close()
    schema = pq.ParquetFile(full_path).schema_arrow.names
    result = {
        "country": country,
        "graph_sha256": sha256(graph),
        "feature_rows": pq.ParquetFile(full_path).metadata.num_rows,
        "graph_rows": pf.metadata.num_rows,
        "row_count_pass": pq.ParquetFile(full_path).metadata.num_rows == pf.metadata.num_rows,
        "schema_pass": all(name in schema for name in scorer.FEATURES) and len(scorer.FEATURES) == 55,
        "feature_count": len(scorer.FEATURES),
        "invalid_feature_counts": {key: int(value) for key, value in invalid.items()},
        "invalid_feature_total": int(sum(invalid.values())),
        "vectorizers": vector_meta,
        "checkpoint_parts": len(tasks),
        "parts_complete": sum(part.get("status") in ("COMPLETE", "SKIPPED") for part in parts),
        "direct_feature_seconds": direct_seconds,
        "context_seconds": context_seconds,
        "total_seconds": time.time() - began,
        "full_features_path": str(full_path.relative_to(MOUNT)),
        "full_features_sha256": sha256(full_path),
        "full_features_bytes": full_path.stat().st_size,
        "peak_rss_mib": psutil.Process().memory_info().rss / 2**20,
    }
    write_json(result, result_path)
    volume.commit()
    return result


def score_country(country: str, volume):
    result_path = STAGE1 / f"scoring_{country}.json"
    ranked_path = STAGE1 / "prethreshold_score_cache" / f"{country}.parquet"
    winner_path = STAGE1 / "target_winners" / f"{country}.parquet"
    if result_path.exists() and ranked_path.exists() and winner_path.exists():
        return json.loads(result_path.read_text(encoding="utf-8"))
    _, scorer = import_frozen()
    began = time.time()
    model_path = FROZEN_STAGE1 / "model.joblib"
    if sha256(FROZEN_STAGE1 / "model.txt") != EXPECTED["model"]:
        raise RuntimeError("Frozen Stage-1 model hash changed")
    model = joblib.load(model_path)
    full = STAGE1 / "full_features" / f"{country}.parquet"
    pf = pq.ParquetFile(full)
    score_dir = STAGE1 / "score_parts" / country
    score_dir.mkdir(parents=True, exist_ok=True)
    scored_rows = 0
    inference_started = time.time()
    for i in range(pf.num_row_groups):
        dest = score_dir / f"part_{i:05d}.parquet"
        if dest.exists():
            scored_rows += pq.ParquetFile(dest).metadata.num_rows
            continue
        frame = pf.read_row_group(i).to_pandas()
        X = frame[scorer.FEATURES].to_numpy(np.float32)
        score = model.predict_proba(X)[:, 1].astype(np.float32)
        data = {
            "s1_id": frame.s1_id,
            "target_id": frame.target_id,
            "source": frame.source,
            "country": frame.country,
            "raw_stage1_score": score,
            "retrieval_view_mask": frame.retrieval_view_mask.to_numpy(np.int16),
        }
        for name in ("name_rank", "compact_name_rank", "address_rank", "combined_rank", "reverse_rank"):
            data[name] = frame[name].to_numpy(np.float32)
        pq.write_table(pa.Table.from_pydict(data), dest, compression="zstd", row_group_size=250_000)
        scored_rows += len(frame)
        if (i + 1) % 10 == 0:
            volume.commit()
        del frame, X, score
    volume.commit()
    inference_seconds = time.time() - inference_started
    ranked_path.parent.mkdir(parents=True, exist_ok=True)
    winner_path.parent.mkdir(parents=True, exist_ok=True)
    cache_started = time.time()
    con = duckdb.connect()
    con.execute("PRAGMA threads=32")
    con.execute("PRAGMA memory_limit='96GB'")
    con.execute(f"PRAGMA temp_directory='/tmp/duckdb_score_{country}'")
    glob = str(score_dir / "*.parquet")
    if not ranked_path.exists():
        con.execute(f"""
            COPY (
              SELECT *,
                     row_number() OVER(PARTITION BY target_id ORDER BY raw_stage1_score DESC,s1_id ASC)::INTEGER AS target_owner_rank,
                     rank() OVER(PARTITION BY target_id ORDER BY raw_stage1_score DESC)::INTEGER AS target_score_rank,
                     count(*) OVER(PARTITION BY target_id)::INTEGER AS owner_candidate_count
              FROM read_parquet('{glob}')
              ORDER BY target_id,target_owner_rank
            ) TO '{ranked_path}' (FORMAT PARQUET,COMPRESSION ZSTD,ROW_GROUP_SIZE 250000)
        """)
        volume.commit()
    if not winner_path.exists():
        con.execute(f"COPY (SELECT * FROM read_parquet('{ranked_path}') WHERE target_owner_rank=1 ORDER BY target_id) TO '{winner_path}' (FORMAT PARQUET,COMPRESSION ZSTD,ROW_GROUP_SIZE 250000)")
        volume.commit()
    distribution = con.execute(
        f"SELECT source,count(*) AS row_count,min(raw_stage1_score) AS min_score,max(raw_stage1_score) AS max_score,"
        "avg(raw_stage1_score) AS mean_score,stddev_pop(raw_stage1_score) AS std_score,"
        "quantile_cont(raw_stage1_score,.01) p01,quantile_cont(raw_stage1_score,.5) p50,"
        "quantile_cont(raw_stage1_score,.9) p90,quantile_cont(raw_stage1_score,.99) p99 "
        f"FROM read_parquet('{ranked_path}') GROUP BY source ORDER BY source"
    ).fetchdf().to_dict("records")
    winner_counts = con.execute(
        f"SELECT count(*) AS \"rows\",count(DISTINCT target_id) AS unique_targets,"
        f"sum(CASE WHEN target_owner_rank<>1 THEN 1 ELSE 0 END) AS bad_rank FROM read_parquet('{winner_path}')"
    ).fetchone()
    con.close()
    cache_seconds = time.time() - cache_started
    result = {
        "country": country,
        "feature_rows": pf.metadata.num_rows,
        "scored_rows": scored_rows,
        "row_count_pass": scored_rows == pf.metadata.num_rows,
        "score_part_count": pf.num_row_groups,
        "score_distribution_by_source": distribution,
        "raw_inference_seconds": inference_seconds,
        "prethreshold_cache_seconds": cache_seconds,
        "total_seconds": time.time() - began,
        "prethreshold_score_cache_path": str(ranked_path.relative_to(MOUNT)),
        "prethreshold_score_cache_sha256": sha256(ranked_path),
        "prethreshold_score_cache_bytes": ranked_path.stat().st_size,
        "target_winner_path": str(winner_path.relative_to(MOUNT)),
        "target_winner_sha256": sha256(winner_path),
        "winner_rows": int(winner_counts[0]),
        "winner_unique_targets": int(winner_counts[1]),
        "winner_uniqueness_pass": winner_counts[0] == winner_counts[1] and winner_counts[2] == 0,
        "peak_rss_mib": psutil.Process().memory_info().rss / 2**20,
    }
    write_json(result, result_path)
    volume.commit()
    return result


def finalize(volume):
    result_path = ROOT / "production_result.json"
    retry_failed_export = False
    if result_path.exists():
        prior_result = json.loads(result_path.read_text(encoding="utf-8"))
        if prior_result.get("production_go"):
            return prior_result
        retry_failed_export = True
    began = time.time()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    matching = OUTPUT / "matching_results.tsv"
    candidates = OUTPUT / "candidate_pairs.tsv"
    ranked_glob = str(STAGE1 / "prethreshold_score_cache" / "*.parquet")
    winner_glob = str(STAGE1 / "target_winners" / "*.parquet")
    graph_glob = str(RETRIEVAL / "candidate_graph" / "*.parquet")
    source1 = TEST / "test_source1.tsv"
    decision_started = time.time()
    con = duckdb.connect()
    con.execute("PRAGMA threads=32")
    con.execute("PRAGMA memory_limit='96GB'")
    con.execute("PRAGMA temp_directory='/tmp/duckdb_finalize'")
    if retry_failed_export or not matching.exists():
        matching_tmp = OUTPUT / "matching_results.tmp.tsv"
        if matching_tmp.exists():
            matching_tmp.unlink()
        con.execute(f"""
            COPY (
              WITH q AS (
                SELECT entity_id AS source1_entity_id
                FROM read_csv('{source1}',delim='\\t',header=true,all_varchar=true)
              ), p AS (
                SELECT s1_id,
                       string_agg(target_id,',' ORDER BY raw_stage1_score DESC,target_id ASC) AS matched_entity_ids
                FROM read_parquet('{winner_glob}')
                WHERE (source='S2' AND raw_stage1_score>={THRESHOLD['S2']})
                   OR (source='S3' AND raw_stage1_score>={THRESHOLD['S3']})
                GROUP BY s1_id
              )
              SELECT q.source1_entity_id,p.matched_entity_ids AS matched_entity_ids
              FROM q LEFT JOIN p ON q.source1_entity_id=p.s1_id
              ORDER BY q.source1_entity_id
            ) TO '{matching_tmp}' (HEADER,DELIMITER '\t',NULL '')
        """)
        os.replace(matching_tmp, matching)
        volume.commit()
    if not candidates.exists():
        con.execute(f"""
            COPY (
              WITH q AS (
                SELECT entity_id AS source1_entity_id
                FROM read_csv('{source1}',delim='\\t',header=true,all_varchar=true)
              ), c AS (
                SELECT s1_id,string_agg(target_id,',' ORDER BY target_id ASC) AS candidate_entity_ids
                FROM read_parquet('{graph_glob}')
                GROUP BY s1_id
              )
              SELECT q.source1_entity_id,coalesce(c.candidate_entity_ids,'') AS candidate_entity_ids
              FROM q LEFT JOIN c ON q.source1_entity_id=c.s1_id
              ORDER BY q.source1_entity_id
            ) TO '{candidates}' (HEADER,DELIMITER '\t',NULL '')
        """)
        volume.commit()
    decision_seconds = time.time() - decision_started
    selected_integrity = con.execute(
        f"WITH s AS (SELECT * FROM read_parquet('{winner_glob}') WHERE raw_stage1_score>=.64) "
        "SELECT count(*) selected_links,count(DISTINCT target_id) unique_targets,"
        "count(*)-count(DISTINCT target_id) duplicate_targets,count(DISTINCT s1_id) nonempty_s1 FROM s"
    ).fetchdf().iloc[0].to_dict()
    score_rows = con.execute(f"SELECT count(*) FROM read_parquet('{ranked_glob}')").fetchone()[0]
    graph_rows = con.execute(f"SELECT count(*) FROM read_parquet('{graph_glob}')").fetchone()[0]
    by_country_source = con.execute(f"""
        WITH q AS (
          SELECT entity_id s1_id,country FROM read_csv('{source1}',delim='\\t',header=true,all_varchar=true)
        ), src AS (SELECT * FROM (VALUES ('S2'),('S3')) v(source)), c AS (
          SELECT s1_id,country,source,count(*) n FROM read_parquet('{graph_glob}') GROUP BY s1_id,country,source
        ), z AS (
          SELECT q.s1_id,q.country,src.source,coalesce(c.n,0) n FROM q CROSS JOIN src LEFT JOIN c USING(s1_id,country,source)
        )
        SELECT country,source,count(*) s1,avg(n) mean,quantile_cont(n,.5) p50,quantile_cont(n,.9) p90,
               quantile_cont(n,.99) p99,max(n) max,sum(CASE WHEN n=0 THEN 1 ELSE 0 END) zero_candidate_s1
        FROM z GROUP BY country,source ORDER BY country,source
    """).fetchdf().to_dict("records")
    output_rows = {
        "matching": sum(1 for _ in matching.open("r", encoding="utf-8")) - 1,
        "candidates": sum(1 for _ in candidates.open("r", encoding="utf-8")) - 1,
    }
    con.close()
    validation_started = time.time()
    validation = subprocess.run(
        [
            sys.executable,
            "/root/validate_submission.py",
            "--matching",
            str(matching),
            "--candidate",
            str(candidates),
            "--test-dir",
            str(TEST),
            "--check-ids",
        ],
        text=True,
        capture_output=True,
        timeout=1800,
    )
    validation_seconds = time.time() - validation_started
    official_validation = {
        "returncode": validation.returncode,
        "pass": validation.returncode == 0,
        "stdout": validation.stdout,
        "stderr": validation.stderr,
    }
    write_json(official_validation, ROOT / "official_validation.json")
    config_hashes = {
        "production_config_sha256": sha256(INPUT / "manifests/production_frozen_config.json"),
        "critical_path_sha256": sha256(INPUT / "manifests/production_critical_path.json"),
        "retrieval_builder_sha256": sha256(CODE / "frozen_full_graph_builder.py"),
        "stage1_scorer_sha256": sha256(CODE / "frozen_stage1_55_scorer.py"),
        "production_source_sha256": sha256(Path(__file__)),
        "model_sha256": sha256(FROZEN_STAGE1 / "model.txt"),
        "feature_schema_sha256": sha256(FROZEN_STAGE1 / "feature_schema.json"),
    }
    transfer = {
        "matching_results": {"path": str(matching.relative_to(MOUNT)), "bytes": matching.stat().st_size, "sha256": sha256(matching)},
        "candidate_pairs": {"path": str(candidates.relative_to(MOUNT)), "bytes": candidates.stat().st_size, "sha256": sha256(candidates)},
        "configuration_hashes": config_hashes,
        "portal_upload_ready": validation.returncode == 0,
        "preserved_v1_unchanged": True,
    }
    write_json(transfer, ROOT / "transfer_manifest.json")
    generations = {country: json.loads((RETRIEVAL / f"generation_{country}.json").read_text()) for country in ("US", "India", "France")}
    features = {country: json.loads((STAGE1 / f"generation_{country}.json").read_text()) for country in ("US", "India", "France")}
    scoring = {country: json.loads((STAGE1 / f"scoring_{country}.json").read_text()) for country in ("US", "India", "France")}
    diagnostics = {
        "schema_and_row_count_integrity": {
            "graph_rows": int(graph_rows),
            "score_rows": int(score_rows),
            "score_equals_graph": score_rows == graph_rows,
            "output_rows": output_rows,
            "expected_s1": 1_732_544,
            "outputs_cover_all_s1": output_rows["matching"] == output_rows["candidates"] == 1_732_544,
            "countries": {country: {"retrieval": generations[country]["queries"], "features": features[country]["feature_rows"], "scores": scoring[country]["scored_rows"]} for country in generations},
        },
        "invalid_features": {country: features[country]["invalid_feature_counts"] for country in features},
        "invalid_feature_totals": {country: features[country]["invalid_feature_total"] for country in features},
        "zero_vectors": {country: generations[country]["zero_vectors"] for country in generations},
        "zero_candidates": {country: {"count": generations[country]["zero_candidate_s1"], "rate": generations[country]["zero_candidate_rate"]} for country in generations},
        "candidate_distribution_by_country_source": by_country_source,
        "score_distribution_by_country_source": {country: scoring[country]["score_distribution_by_source"] for country in scoring},
        "selected_integrity": {key: int(value) for key, value in selected_integrity.items()},
        "deterministic_uniqueness_pass": all(scoring[country]["winner_uniqueness_pass"] for country in scoring) and int(selected_integrity["duplicate_targets"]) == 0,
        "official_validation": official_validation,
    }
    write_json(diagnostics, ROOT / "production_diagnostics.json")
    result = {
        "status": "COMPLETE" if official_validation["pass"] and diagnostics["deterministic_uniqueness_pass"] and diagnostics["schema_and_row_count_integrity"]["score_equals_graph"] else "BLOCKED",
        "production_go": bool(official_validation["pass"]),
        "thresholds": THRESHOLD,
        "score_cache_path": str((STAGE1 / "prethreshold_score_cache").relative_to(MOUNT)),
        "matching_results_path": str(matching.relative_to(MOUNT)),
        "candidate_pairs_path": str(candidates.relative_to(MOUNT)),
        "matching_results_sha256": transfer["matching_results"]["sha256"],
        "candidate_pairs_sha256": transfer["candidate_pairs"]["sha256"],
        "selected_links": int(selected_integrity["selected_links"]),
        "empty_s1": 1_732_544 - int(selected_integrity["nonempty_s1"]),
        "official_validation_pass": official_validation["pass"],
        "configuration_hashes": config_hashes,
        "timing": {
            "decision_export_seconds": decision_seconds,
            "official_validation_seconds": validation_seconds,
            "finalize_total_seconds": time.time() - began,
            "retrieval_wall_proxy_seconds": max(v["total_seconds"] for v in generations.values()),
            "feature_wall_proxy_seconds": max(v["total_seconds"] for v in features.values()),
            "score_wall_proxy_seconds": max(v["total_seconds"] for v in scoring.values()),
        },
        "peak_rss_mib": psutil.Process().memory_info().rss / 2**20,
        "test_accessed": True,
        "final_holdout_accessed": False,
        "blockers": [] if official_validation["pass"] else ["official_submission_validation_failed"],
    }
    write_json(result, result_path)
    volume.commit()
    return result
