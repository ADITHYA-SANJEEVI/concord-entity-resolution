"""Headless frontier plots, with the population and diagnostic claim boundary."""

from pathlib import Path


def plot_frontier(report: dict, population: str, path: str | Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    points = report["points"]
    costs = (("candidate_pairs", "Candidate pairs"), ("wall_seconds", "Wall time (seconds)"),
             ("peak_process_rss_bytes", "Process lifetime peak RSS (MiB)"))
    with plt.rc_context({"svg.hashsalt": "concord.retrieval-frontier.v1"}):
        figure, axes = plt.subplots(1, 3, figsize=(13, 4), constrained_layout=True)
        for axis, (cost, label) in zip(axes, costs, strict=True):
            groups = {}
            for point in points:
                recall = point["truth_pair_recall"]
                if recall is None:
                    continue
                x = point[cost] / 2**20 if cost == "peak_process_rss_bytes" else point[cost]
                pareto = point[f"pareto_{cost}"]
                groups.setdefault((x, recall, pareto), []).append(
                    str(point["configuration"]["budgets"][0]))
            for (x, recall, pareto), budgets in groups.items():
                axis.scatter(x, recall, color="#126e55" if pareto else "#777777",
                             marker="o" if pareto else "x", s=55,
                             label="K=" + ",".join(budgets))
            axis.set_xlabel(label)
            axis.set_ylabel("Truth-pair recall")
            axis.set_ylim(-.05, 1.05)
            axis.grid(alpha=.2)
            if groups:
                axis.legend(loc="lower right", fontsize=8)
        figure.suptitle(f"{population}\nDiagnostic frontier: green = Pareto-nondominated; "
                        "no promotion claim", fontsize=11)
        figure.savefig(path, metadata={"Date": None})
        plt.close(figure)
