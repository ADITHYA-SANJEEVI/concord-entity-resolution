"""Numerical compatibility reference used by Concord contract tests."""

import hashlib
import time
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sparse_dot_topn import sp_matmul_topn

MOUNT = Path("/volume")
OUT = MOUNT / "output"
K = {"name": 5, "compact": 5, "address": 5, "combined": 10, "reverse": 8}
SEED = 0
FIT_CAP = 3_000_000
CHUNK = 250_000


def fold(x):
    return (
        "".join(
            c for c in unicodedata.normalize("NFKD", str(x)) if not unicodedata.combining(c)
        ).casefold()
        if x is not None
        else ""
    )


def sha_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def commit(volume):
    volume.commit()


def vec(view):
    base = dict(
        min_df=2,
        max_df=0.05,
        sublinear_tf=True,
        dtype=np.float32,
        lowercase=False,
        norm="l2",
        use_idf=True,
        smooth_idf=True,
    )
    if view == "name":
        return TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 3), **base)
    if view == "compact":
        return TfidfVectorizer(analyzer="char", ngram_range=(3, 3), **base)
    return TfidfVectorizer(analyzer="word", token_pattern="[a-z0-9]+", **base)


def fit_transform(q, t, view, country, volume):
    field = "name" if view in ("name", "compact") else "address"
    qa = [r[field].replace(" ", "") if view == "compact" else r[field] for r in q]
    ta = [r[field].replace(" ", "") if view == "compact" else r[field] for r in t]
    ids = np.array(
        ["q:" + r["s1_id"] for r in q] + ["t:" + r["target_id"] for r in t], dtype=object
    )
    text = qa + ta
    rng = np.random.default_rng(SEED)
    selected = (
        np.arange(len(text))
        if len(text) <= FIT_CAP
        else np.sort(rng.choice(len(text), size=FIT_CAP, replace=False))
    )
    sample = OUT / "vectorizer_samples" / f"{country}_{view}.txt"
    sample.parent.mkdir(parents=True, exist_ok=True)
    sample.write_text("\n".join(ids[selected]) + "\n")
    commit(volume)
    v = vec(view)
    v.fit([text[int(i)] for i in selected])
    qm = v.transform(qa).astype(np.float32)
    tm = v.transform(ta).astype(np.float32)
    return (
        qm,
        tm,
        {
            "view": view,
            "vocabulary": len(v.vocabulary_),
            "sample_path": str(sample.relative_to(MOUNT)),
            "sample_sha256": sha_file(sample),
            "shape_q": list(qm.shape),
            "shape_t": list(tm.shape),
            "nnz_q": int(qm.nnz),
            "nnz_t": int(tm.nnz),
        },
    )


def retrieve(view, q, t, Q, T, country, volume):
    base = OUT / "checkpoints" / country / view
    base.mkdir(parents=True, exist_ok=True)
    TT = T.T.tocsr()
    items = []
    began = time.perf_counter()
    for start in range(0, Q.shape[0], CHUNK):
        dest = base / f"chunk_{start:09d}.parquet"
        if dest.exists():
            continue
        C = sp_matmul_topn(
            Q[start : start + CHUNK], TT, top_n=K[view], threshold=0.0, sort=True, n_threads=32
        ).tocoo()
        qi = C.row.astype(np.int64) + start
        ti = C.col.astype(np.int64)
        score = C.data.astype(np.float32)
        order = np.lexsort((-score, qi))
        qi, ti, score = (qi[order], ti[order], score[order])
        starts = np.r_[0, np.flatnonzero(np.diff(qi)) + 1] if len(qi) else np.empty(0, np.int64)
        rank = (
            (np.arange(len(qi)) - np.repeat(starts, np.diff(np.r_[starts, len(qi)]))).astype(
                np.int16
            )
            if len(qi)
            else np.empty(0, np.int16)
        )
        if view == "reverse":
            s1 = np.array([t[int(i)]["target_id"] for i in qi], dtype=object)
            target = np.array([q[int(i)]["s1_id"] for i in ti], dtype=object)
            s1, target = (target, s1)
        else:
            s1 = np.array([q[int(i)]["s1_id"] for i in qi], dtype=object)
            target = np.array([t[int(i)]["target_id"] for i in ti], dtype=object)
        col = "combined" if view == "reverse" else view
        frame = pd.DataFrame(
            {"s1_id": s1, "target_id": target, f"{col}_cosine": score, f"{view}_rank": rank}
        )
        frame.to_parquet(dest, index=False)
        commit(volume)
        items.append({"chunk": start, "pairs": len(frame), "seconds": time.perf_counter() - began})
        del C, frame
    return items
