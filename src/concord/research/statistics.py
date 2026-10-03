"""Predeclared paired query-unit diagnostics; no automatic promotion."""

import math

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score


def paired_mean_interval(a, b, seed=2026, repetitions=1000):
    if len(a) != len(b) or not len(a):
        raise ValueError("paired nonempty population required")
    delta = np.asarray(b, dtype=float) - np.asarray(a, dtype=float)
    if not np.isfinite(delta).all() or type(repetitions) is not int or repetitions < 1:
        raise ValueError("finite paired values and positive bootstrap count required")
    rng = np.random.default_rng(seed)
    samples = delta[rng.integers(0, len(delta), (repetitions, len(delta)))].mean(axis=1)
    return {"delta": float(delta.mean()), "ci95": np.quantile(samples, [.025, .975]).tolist(),
            "query_count": len(delta), "bootstrap_repetitions": repetitions, "seed": seed,
            "meaning": "paired synthetic query bootstrap; descriptive, not population or equivalence proof"}


def risk_metrics(query_ids, errors, risks):
    if not (len(query_ids) == len(errors) == len(risks)) or len(set(query_ids)) != len(query_ids):
        raise ValueError("one aligned risk/error per unique query required")
    if any(e not in (0, 1) for e in errors) or any(not math.isfinite(r) for r in risks):
        raise ValueError("finite risk and binary error required")
    order = sorted(range(len(errors)), key=lambda i: (risks[i], query_ids[i]))
    curve = [{"coverage": n / len(order), "risk": float(np.mean([errors[i] for i in order[:n]]))}
             for n in range(1, len(order) + 1)]
    return {"query_count": len(order), "error_count": sum(errors),
            "auroc_error": float(roc_auc_score(errors, risks)) if len(set(errors)) == 2 else None,
            "auprc_error": float(average_precision_score(errors, risks)) if len(set(errors)) == 2 else None,
            "risk_at_90": curve[math.ceil(.9 * len(order)) - 1]["risk"] if order else None,
            "risk_at_95": curve[math.ceil(.95 * len(order)) - 1]["risk"] if order else None,
            "risk_coverage": curve}


def risk_comparison(query_ids, errors, confidence, structure, seed=2026, repetitions=500):
    if not errors or type(repetitions) is not int or repetitions < 1:
        raise ValueError("nonempty population and positive bootstrap count required")
    a, b = risk_metrics(query_ids, errors, confidence), risk_metrics(query_ids, errors, structure)
    rng, deltas, pr_deltas = np.random.default_rng(seed), [], []
    for _ in range(repetitions):
        indices = rng.integers(0, len(errors), len(errors))
        y = np.array(errors)[indices]
        if len(set(y.tolist())) == 2:
            deltas.append(float(roc_auc_score(y, np.array(structure)[indices]) - roc_auc_score(y, np.array(confidence)[indices])))
            pr_deltas.append(float(average_precision_score(y, np.array(structure)[indices]) - average_precision_score(y, np.array(confidence)[indices])))
    ci = np.quantile(deltas, [.025, .975]).tolist() if deltas else None
    return {"confidence": a, "structure": b, "auroc_delta": b["auroc_error"] - a["auroc_error"] if deltas else None,
            "paired_auroc_delta_ci95": ci, "valid_bootstrap_samples": len(deltas),
            "auprc_delta": b["auprc_error"] - a["auprc_error"] if pr_deltas else None,
            "paired_auprc_delta_ci95": np.quantile(pr_deltas, [.025, .975]).tolist() if pr_deltas else None,
            "requested_bootstrap_samples": repetitions, "seed": seed,
            "conclusion": "descriptive improvement" if ci and ci[0] > 0 else
                          "descriptive degradation" if ci and ci[1] < 0 else "no clear evidence of difference",
            "limitation": "Synthetic query units can share targets and generator templates; no external-generalization or equivalence claim."}
