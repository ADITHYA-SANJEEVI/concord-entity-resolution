"""Numerical compatibility reference used by Concord contract tests."""

import re
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler

from concord.features.reference import FEATURE_NAMES

BASE_FEATURES = list(FEATURE_NAMES[:38])
WORD = re.compile(r"\w+", re.UNICODE)
NUM = re.compile(r"\d+")
_G = {}


def tri(value: str) -> frozenset[str]:
    return frozenset(value[i : i + 3] for i in range(max(0, len(value) - 2)))


def rep(name: str, address: str):
    nt = frozenset(WORD.findall(name))
    at = frozenset(WORD.findall(address))
    nums = tuple(NUM.findall(address))
    ns = frozenset(nums)
    return (nt, at, tri(name), tri(address), ns, nums[0] if nums else "")


def overlap(a, b):
    inter = len(a & b)
    union = len(a | b)
    return (
        inter,
        inter / union if union else 0.0,
        inter / len(a) if a else 0.0,
        inter / len(b) if b else 0.0,
    )


def direct(qname, qaddr, tname, taddr, source, qrep=None, trep=None):
    qn, qa, qtri, qatri, qnums, qfirst = qrep if qrep is not None else rep(qname, qaddr)
    tn, ta, ttri, tatri, tnums, tfirst = trep if trep is not None else rep(tname, taddr)
    _, nj, nqc, ntc = overlap(qn, tn)
    _, ntj, _, _ = overlap(qtri, ttri)
    _, aj, aqc, atc = overlap(qa, ta)
    _, atj, _, _ = overlap(qatri, tatri)
    _, numj, numqc, numtc = overlap(qnums, tnums)
    nf = (
        [
            fuzz.ratio(qname, tname) / 100.0,
            JaroWinkler.normalized_similarity(qname, tname),
            fuzz.token_sort_ratio(qname, tname) / 100.0,
            fuzz.token_set_ratio(qname, tname) / 100.0,
            fuzz.partial_ratio(qname, tname) / 100.0,
        ]
        if qname and tname
        else [0.0] * 5
    )
    af = (
        [
            fuzz.ratio(qaddr, taddr) / 100.0,
            fuzz.token_sort_ratio(qaddr, taddr) / 100.0,
            fuzz.token_set_ratio(qaddr, taddr) / 100.0,
        ]
        if qaddr and taddr
        else [0.0] * 3
    )
    return [
        float(bool(qname) and qname == tname),
        *nf,
        ntj,
        nj,
        nqc,
        ntc,
        float(bool(qaddr) and qaddr == taddr),
        *af,
        atj,
        aj,
        aqc,
        atc,
        numj,
        numqc,
        numtc,
        float(bool(qfirst) and qfirst == tfirst),
        float(len(qnums)),
        float(len(tnums)),
        float(not bool(qname)),
        float(not bool(tname)),
        float(not bool(qaddr)),
        float(not bool(taddr)),
        float(source == "S2"),
    ]


def coord(Q, T, qi, ti):
    return np.asarray(Q[qi].multiply(T[ti]).sum(axis=1)).ravel().astype(np.float32, copy=False)


def _worker(task):
    country, row_group, destination = task
    destination = Path(destination)
    if destination.exists():
        return {"row_group": row_group, "status": "SKIPPED"}
    began = time.perf_counter()
    graph = pq.ParquetFile(_G["graph"])
    table = graph.read_row_group(row_group)
    frame = table.to_pandas()
    qi = np.fromiter((_G["qmap"][x] for x in frame.s1_id), dtype=np.int64, count=len(frame))
    ti = np.fromiter((_G["tmap"][x] for x in frame.target_id), dtype=np.int64, count=len(frame))
    en = coord(_G["Qn"], _G["Tn"], qi, ti)
    ec = coord(_G["Qc"], _G["Tc"], qi, ti)
    ea = coord(_G["Qa"], _G["Ta"], qi, ti)
    matrix = np.empty((len(frame), 38), dtype=np.float32)
    qcache = {}
    tcache = {}
    for i, (qix, tix, src) in enumerate(zip(qi, ti, frame.source, strict=True)):
        qr = _G["q"][int(qix)]
        tr = _G["t"][int(tix)]
        if qix not in qcache:
            qcache[qix] = rep(qr["name"], qr["address"])
        if tix not in tcache:
            tcache[tix] = rep(tr["name"], tr["address"])
        matrix[i, :29] = direct(
            qr["name"], qr["address"], tr["name"], tr["address"], src, qcache[qix], tcache[tix]
        )
    matrix[:, 29] = en
    matrix[:, 30] = ec
    matrix[:, 31] = ea
    matrix[:, 32] = np.float32(0.5) * en + np.float32(0.5) * ea
    for j, col in enumerate(
        ("name_rank", "compact_name_rank", "address_rank", "combined_rank", "reverse_rank"),
        start=33,
    ):
        matrix[:, j] = frame[col].to_numpy(np.float32)
    data = {
        "s1_id": frame.s1_id,
        "target_id": frame.target_id,
        "country": frame.country,
        "source": frame.source,
        "retrieval_view_mask": frame.retrieval_view_mask.to_numpy(np.int16),
    }
    data.update({name: matrix[:, i] for i, name in enumerate(BASE_FEATURES)})
    destination.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.Table.from_pydict(data), destination, compression="zstd", row_group_size=250000
    )
    return {
        "row_group": row_group,
        "rows": len(frame),
        "seconds": time.perf_counter() - began,
        "status": "COMPLETE",
    }


def _context_sql(country, base_glob, dest):
    signals = ("name", "address", "combined")
    w1 = []
    for s in signals:
        score = f"exact_{s}_cosine"
        w1 += [
            f"rank() OVER(PARTITION BY s1_id,source ORDER BY {score} DESC) AS {s}_query_source_rank",
            f"max({score}) OVER(PARTITION BY s1_id,source) AS {s}_qbest",
            f"rank() OVER(PARTITION BY target_id ORDER BY {score} DESC) AS {s}_target_owner_rank",
            f"max({score}) OVER(PARTITION BY target_id) AS {s}_tbest",
        ]
    w2 = []
    for s in signals:
        score = f"exact_{s}_cosine"
        w2 += [
            f"sum(CASE WHEN {score}={s}_tbest THEN 1 ELSE 0 END) OVER(PARTITION BY target_id) AS {s}_topcount",
            f"max(CASE WHEN {score}<{s}_tbest THEN {score} END) OVER(PARTITION BY target_id) AS {s}_second",
        ]
    context = []
    for s in signals:
        score = f"exact_{s}_cosine"
        context += [
            f"{s}_query_source_rank::FLOAT AS {s}_query_source_rank",
            f"({score}-{s}_qbest)::FLOAT AS {s}_query_source_delta_best",
            f"{s}_target_owner_rank::FLOAT AS {s}_target_owner_rank",
            f"({score}-{s}_tbest)::FLOAT AS {s}_target_delta_best",
            f"(CASE WHEN target_count=1 THEN 0 WHEN {score}={s}_tbest AND {s}_topcount=1 THEN {score}-coalesce({s}_second,{score}) ELSE {score}-{s}_tbest END)::FLOAT AS {s}_target_rival_margin",
        ]
    return f"COPY (WITH b AS (SELECT * FROM read_parquet('{base_glob}')), w1 AS (SELECT *,count(*) OVER(PARTITION BY s1_id,source) candidate_count_within_s1_source,count(*) OVER(PARTITION BY target_id) target_count,{','.join(w1)} FROM b), w2 AS (SELECT *,{','.join(w2)} FROM w1) SELECT s1_id,target_id,country,source,retrieval_view_mask,{','.join(BASE_FEATURES)},{','.join(context)},candidate_count_within_s1_source::FLOAT candidate_count_within_s1_source,target_count::FLOAT distinct_competing_s1_count_for_target FROM w2 ORDER BY s1_id,target_id) TO '{dest}' (FORMAT PARQUET,COMPRESSION ZSTD,ROW_GROUP_SIZE 250000)"
