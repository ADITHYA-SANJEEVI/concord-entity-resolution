"""Per-query set quality and descriptive pair calibration; populations are explicit."""

from collections import defaultdict

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from concord.c3_contracts import probability
from concord.contracts import require_id


def set_metrics(truth: frozenset[str], prediction: frozenset[str]) -> dict:
    hits = len(truth & prediction)
    precision = hits / len(prediction) if prediction else float(not truth)
    recall = hits / len(truth) if truth else 1.
    f05 = 1.25 * precision * recall / (.25 * precision + recall) if precision + recall else 0.
    return {"f05": f05, "precision": precision, "recall": recall,
            "exact_set": float(truth == prediction), "tp": hits,
            "fp": len(prediction - truth), "fn": len(truth - prediction)}


def quality_report(query_ids: tuple[str, ...], truth: tuple[tuple[str, str], ...], decisions,
                   population: str) -> dict:
    require_id(population)
    if len(set(query_ids)) != len(query_ids) or len(set(truth)) != len(truth):
        raise ValueError("duplicate queries or truth pairs")
    predictions = {d.s1_id: frozenset(d.accepted_targets) for d in decisions}
    if len(predictions) != len(decisions) or set(predictions) != set(query_ids):
        raise ValueError("decisions must cover exactly the evaluated query population")
    emitted = [t for d in decisions for t in d.accepted_targets]
    if len(emitted) != len(set(emitted)):
        raise ValueError("a target cannot be accepted by multiple queries")
    truths = defaultdict(set)
    for query, target in truth:
        if query not in predictions:
            raise ValueError("truth outside evaluation population")
        require_id(target)
        truths[query].add(target)
    rows = []
    for query in sorted(query_ids):
        size = len(truths[query])
        cohort = "zero_match" if not size else "single_match" if size == 1 else "multi_match"
        rows.append({"s1_id": query, "truth_cohort": cohort,
                     **set_metrics(frozenset(truths[query]), predictions[query])})

    def aggregate(values):
        return {"query_count": len(values),
                **{f"macro_{key}" if key != "exact_set" else "exact_set_accuracy":
                   float(np.mean([r[key] for r in values])) if values else None
                   for key in ("f05", "precision", "recall", "exact_set")},
                **{key: sum(r[key] for r in values) for key in ("tp", "fp", "fn")}}

    return {"schema_version": "concord.set-quality.v1", "population": population,
            **aggregate(rows), "accepted_link_count": len(emitted),
            "cohorts": {kind: aggregate([r for r in rows if r["truth_cohort"] == kind])
                        for kind in ("zero_match", "single_match", "multi_match")}, "per_query": rows,
            "empty_set_convention": "empty/empty: P=R=F=1; empty truth/nonempty prediction: P=F=0,R=1; missing prediction with truth: P=R=F=0"}


def calibration_report(labels: tuple[int, ...], scores: tuple[float, ...], population: str,
                       bins: int = 10) -> dict:
    require_id(population)
    if len(labels) != len(scores) or any(type(y) is not int or y not in (0, 1) for y in labels):
        raise ValueError("one binary label per scored pair required")
    if type(bins) is not int or bins < 1:
        raise ValueError("positive bin count required")
    for score in scores:
        probability(score)
    y, p = np.asarray(labels), np.asarray(scores, dtype=float)
    reliability = []
    for index in range(bins):
        mask = (p >= index / bins) & ((p < (index + 1) / bins) if index < bins - 1 else (p <= 1))
        reliability.append({"lower": index / bins, "upper": (index + 1) / bins,
                            "count": int(mask.sum()), "mean_score": float(p[mask].mean()) if mask.any() else None,
                            "positive_fraction": float(y[mask].mean()) if mask.any() else None})
    distributions = {}
    for value, name in ((0, "negative"), (1, "positive")):
        selected = p[y == value]
        distributions[name] = {"count": len(selected), "mean": float(selected.mean()) if len(selected) else None,
                               "min": float(selected.min()) if len(selected) else None,
                               "max": float(selected.max()) if len(selected) else None}
    return {"schema_version": "concord.calibration.v1", "population": population, "pair_count": len(y),
            "auroc": float(roc_auc_score(y, p)) if len(set(labels)) == 2 else None,
            "auprc": float(average_precision_score(y, p)) if 1 in labels and 0 in labels else None,
            "log_loss": float(log_loss(y, p, labels=[0, 1])) if len(y) else None,
            "brier_score": float(brier_score_loss(y, p)) if len(y) else None,
            "ece": sum(b["count"] * abs(b["mean_score"] - b["positive_fraction"])
                       for b in reliability if b["count"]) / len(y) if len(y) else None,
            "bins": reliability, "score_distributions": distributions,
            "calibration_slope": None, "calibration_intercept": None,
            "limitation": "Descriptive fixture diagnostics only; no calibration transform or threshold tuning. Slope/intercept not estimated."}
