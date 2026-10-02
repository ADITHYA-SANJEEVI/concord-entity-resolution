"""Candidate-only diagnostics, never final-resolution or stability claims."""

from collections import Counter
from dataclasses import asdict

import numpy as np

from concord.contracts import LANES, EntityRecord, RetrievalCandidate
from concord.identity import canonical_records
from concord.metadata import content_sha256
from concord.retrieval.baseline import RetrievalRun
from concord.storage import canonical_candidates


def evaluate_retrieval(records: tuple[EntityRecord, ...],
                       candidates: tuple[RetrievalCandidate, ...],
                       truth: tuple[tuple[str, str], ...] | None = None) -> dict:
    records = canonical_records(records)
    candidates = canonical_candidates(candidates)
    queries = {r.entity_id: r for r in records if r.source == "S1"}
    targets = {r.entity_id: r for r in records if r.source != "S1"}
    if len(targets) != sum(r.source != "S1" for r in records):
        raise ValueError("ambiguous target IDs")
    for c in candidates:
        if c.s1_id not in queries or c.target_id not in targets:
            raise ValueError("candidate references an unknown entity")
        if (queries[c.s1_id].country != targets[c.target_id].country
                or c.country != queries[c.s1_id].country
                or c.target_source != targets[c.target_id].source):
            raise ValueError("candidate violates eligibility/source semantics")
    if truth is not None:
        if len(set(truth)) != len(truth):
            raise ValueError("duplicate truth pair")
        for query, target in truth:
            if query not in queries or target not in targets:
                raise ValueError("truth references an unknown entity")
            if queries[query].country != targets[target].country:
                raise ValueError("truth outside declared eligible country universe")
    truths = set(truth or ())
    pairs = {(c.s1_id, c.target_id) for c in candidates}
    hits = len(truths & pairs)
    counts = Counter(c.s1_id for c in candidates)
    density = [counts[q] for q in queries]
    qcountries = Counter(r.country for r in queries.values())
    tcountries = Counter(r.country for r in targets.values())
    eligible = sum(n * tcountries[country] for country, n in qcountries.items())
    # No calibrated global ranking exists before C3. R@K is reported per forward
    # lane and as an explicitly named union of each forward lane's top K.
    ranked = {}
    for lane in LANES[:-1]:
        ranked[lane] = {str(k): (sum(
            (c.s1_id, c.target_id) in truths and any(e.lane == lane and e.rank <= k
                                                   for e in c.lane_evidence)
            for c in candidates) / len(truths) if truths else None)
            for k in (1, 5, 10, 20)}
    union_at_k = {str(k): (sum(
        (c.s1_id, c.target_id) in truths and any(e.lane != "reverse" and e.rank <= k
                                               for e in c.lane_evidence)
        for c in candidates) / len(truths) if truths else None) for k in (1, 5, 10, 20)}
    lane_pairs = {lane: {(c.s1_id, c.target_id) for c in candidates
                         if any(e.lane == lane for e in c.lane_evidence)} for lane in LANES}
    rescue, ablation = {}, {}
    for lane in LANES:
        without = {(c.s1_id, c.target_id) for c in candidates if c.available_without(lane)}
        added = len(pairs - without)
        unique_hits = len((pairs - without) & truths)
        recall_delta = unique_hits / len(truths) if truths else None
        rescue[lane] = {
            "candidate_pairs": len(lane_pairs[lane]), "uniquely_added_candidates": added,
            "truths_recovered": len(lane_pairs[lane] & truths) if truth is not None else None,
            "unique_truths_rescued": unique_hits if truth is not None else None,
            "marginal_recall_per_million_added_candidates": (
                recall_delta * 1_000_000 / added if added and recall_delta is not None else None),
        }
        ablation[lane] = {
            "candidate_pairs": len(without), "candidate_pairs_lost": added,
            "truths_lost": unique_hits if truth is not None else None,
            "truth_pair_recall": len(without & truths) / len(truths) if truths else None,
        }
    return {
        "candidate_pairs": len(candidates), "queries": len(queries), "targets": len(targets),
        "eligible_cartesian_pairs": eligible,
        "reduction_ratio": 1 - len(candidates) / eligible if eligible else None,
        "density": {"mean": float(np.mean(density)) if density else None,
                    **{p: float(np.quantile(density, q)) if density else None
                       for p, q in (("p50", .5), ("p90", .9), ("p99", .99))},
                    "max": max(density) if density else None},
        "zero_candidate_queries": sum(counts[q] == 0 for q in queries),
        "zero_candidate_rate": sum(counts[q] == 0 for q in queries) / len(queries)
                               if queries else None,
        "truth_pairs": len(truths) if truth is not None else None,
        "truths_recovered": hits if truth is not None else None,
        "truth_pair_recall": hits / len(truths) if truths else None,
        "candidates_per_recovered_truth": len(candidates) / hits if hits else None,
        "recall_at_k_by_forward_lane": ranked,
        "recall_at_k_forward_lane_union": union_at_k,
        "ranking_semantics": "one-based per forward lane; union@K is not global top-K; "
                             "reverse ranks targets' S1 neighbors, so reverse R@K is undefined",
        "lane_rescue": rescue,
        "lane_overlap_candidates": {
            a: {b: len(lane_pairs[a] & lane_pairs[b]) for b in LANES} for a in LANES},
        "lane_overlap_truths": {
            a: {b: len(lane_pairs[a] & lane_pairs[b] & truths) if truth is not None else None
                for b in LANES} for a in LANES},
        "truths_by_lane_count": {str(n): sum(
            (c.s1_id, c.target_id) in truths and c.contributing_lane_count == n
            for c in candidates) if truth is not None else None for n in range(1, 6)},
        "leave_one_lane_out_candidate_availability": ablation,
        "truth_fingerprint": content_sha256(sorted(truths)) if truth is not None else None,
    }


def candidate_fingerprint(candidates: tuple[RetrievalCandidate, ...]) -> str:
    return content_sha256({"schema_version": "concord.retrieval-candidate.v1",
                           "rows": [asdict(c) for c in canonical_candidates(candidates)]})


def frontier(records: tuple[EntityRecord, ...], runs: tuple[RetrievalRun, ...],
             truth: tuple[tuple[str, str], ...]) -> dict:
    points = []
    for run in runs:
        report = evaluate_retrieval(records, run.candidates, truth)
        points.append({
            "configuration_fingerprint": run.config.fingerprint,
            "configuration": asdict(run.config), "candidate_pairs": len(run.candidates),
            "truth_pair_recall": report["truth_pair_recall"],
            "wall_seconds": run.wall_seconds, "sampled_peak_rss_bytes": run.sampled_peak_rss_bytes,
            "peak_process_rss_bytes": run.peak_process_rss_bytes,
            "candidate_fingerprint": candidate_fingerprint(run.candidates),
            "fit_evidence": [asdict(e) for e in run.fit_evidence],
            "warnings": run.warnings,
        })
    for cost in ("candidate_pairs", "wall_seconds", "sampled_peak_rss_bytes",
                 "peak_process_rss_bytes"):
        for p in points:
            recall = p["truth_pair_recall"]
            p[f"pareto_{cost}"] = (None if recall is None else not any(
                other["truth_pair_recall"] is not None
                and other["truth_pair_recall"] >= recall and other[cost] <= p[cost]
                and (other["truth_pair_recall"] > recall or other[cost] < p[cost])
                for other in points))
    return {"schema_version": "concord.retrieval-frontier.v1", "points": points,
            "promotion": "DIAGNOSTIC_ONLY", "primary_cost": "candidate_pairs",
            "memory_semantics": "actual process-lifetime high-water plus sampled RSS; "
                                "includes interpreter/dependencies and earlier frontier points; "
                                "not isolated stage memory"}
