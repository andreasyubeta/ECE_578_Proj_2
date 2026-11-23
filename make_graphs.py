"""Render the report graphs from the task CSV exports into outputs/*.png.

Run task1.py through task7.py first; this script only reads outputs/*.csv.
"""

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402


PROJECT_DIR = Path(__file__).resolve().parent
OUT = PROJECT_DIR / "outputs"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID, SURFACE = "#1f1f1e", "#6b6a64", "#e4e3df", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": INK, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold", "legend.frameon": False,
})
thousands = FuncFormatter(lambda v, _: f"{v:,.0f}")


def rows(name: str) -> list[dict[str, str]]:
    with (OUT / name).open(encoding="utf-8") as source:
        return list(csv.DictReader(source))


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=200)
    plt.close(fig)
    print("wrote", OUT / name)


def graph1() -> None:
    data = rows("task1.csv")
    categories = [r["category"] for r in data]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    for ax, year, color in zip(axes, ("2015", "2021"), (BLUE, ORANGE)):
        counts = [int(r[f"{year}_count"]) for r in data]
        shares = [float(r[f"{year}_share_percent"]) for r in data]
        total = int(data[0][f"{year}_total_classified"])
        bars = ax.bar(categories, counts, color=color, width=0.6)
        for bar, count, share in zip(bars, counts, shares):
            ax.annotate(f"{count:,}\n({share:.1f}%)", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        ha="center", va="bottom", xytext=(0, 3), textcoords="offset points", fontsize=9)
        snapshot = "Aug 1, 2015" if year == "2015" else "Apr 1, 2021"
        ax.set_title(f"{snapshot} (n = {total:,} classified ASes)")
        ax.set_xlabel("CAIDA business category")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Number of ASes")
    axes[0].yaxis.set_major_formatter(thousands)
    axes[0].set_ylim(0, max(int(r["2021_count"]) for r in data) * 1.18)
    fig.suptitle("Graph 1: AS business classification by category (share of each year's classified ASes)",
                 fontweight="bold")
    save(fig, "graph1_classification.png")


def graph2() -> None:
    data = rows("task2b.csv")
    bins = [r["degree_bin"] for r in data]
    total = sum(int(r["global_as_count"]) for r in data)
    panels = (("global_as_count", "Global degree $d_i$"), ("customer_as_count", "Customer degree $d_i^{(c)}$"),
              ("peer_as_count", "Peer degree $d_i^{(p)}$"), ("provider_as_count", "Provider degree $d_i^{(r)}$"))
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharey=True)
    for ax, (field, title) in zip(axes.flat, panels):
        counts = [int(r[field]) for r in data]
        bars = ax.bar(bins, counts, color=BLUE, width=0.7)
        for bar, count in zip(bars, counts):
            ax.annotate(f"{count:,}", (bar.get_x() + bar.get_width() / 2, max(count, 1)), ha="center",
                        va="bottom", xytext=(0, 2), textcoords="offset points", fontsize=8)
        ax.set_yscale("log")
        ax.set_ylim(0.8, total * 3)
        ax.set_title(title)
        ax.set_xlabel("Degree bin (number of neighboring ASes)")
        ax.tick_params(axis="x", labelsize=8.5)
        ax.grid(axis="x", visible=False)
    for ax in axes[:, 0]:
        ax.set_ylabel("Number of ASes (log scale)")
    fig.suptitle(f"Graph 2: AS degree histograms, Nov 2024 relationship graph (n = {total:,} ASes)",
                 fontweight="bold")
    save(fig, "graph2_degree_histograms.png")


def graph3() -> None:
    data = rows("task2c.csv")
    summary = data[0]
    ccdf = [r for r in data[1:] if int(r["as_count_at_least_threshold"]) > 0]
    k = [int(r["degree_threshold"]) for r in ccdf]
    p = [float(r["ccdf"]) for r in ccdf]
    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.step(k, p, where="post", color=BLUE, linewidth=2)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Global degree threshold k (neighboring ASes, log scale)")
    ax.set_ylabel("Pr(D ≥ k) (fraction of all graph ASes, log scale)")
    stats = (f"n = {int(summary['total_as_count']):,} ASes\nmean = {float(summary['mean_global_degree']):.2f}\n"
             f"median = {float(summary['median_global_degree']):g}\n95th pct = {summary['p95_global_degree']}\n"
             f"max = {int(summary['max_global_degree']):,}")
    ax.text(0.97, 0.97, stats, transform=ax.transAxes, ha="right", va="top", fontsize=9,
            bbox={"facecolor": SURFACE, "edgecolor": GRID})
    ax.set_title("Graph 3: CCDF of global AS degree, Nov 2024 (k ≥ 1)")
    save(fig, "graph3_degree_ccdf.png")


def graph4() -> None:
    data = rows("task3b.csv")
    for quantity, name, title, xlabel in (
        ("prefix_count", "graph4a_prefix_count.png", "Graph 4a: Distinct advertised IPv4 prefixes per origin AS",
         "Distinct prefixes $P_i$ (power-of-2 bins, log scale)"),
        ("unique_address_count", "graph4b_address_count.png",
         "Graph 4b: Unique advertised IPv4 addresses per origin AS",
         "Unique IPv4 addresses $A_i$ (power-of-2 bins, log scale)"),
    ):
        part = [r for r in data if r["quantity"] == quantity]
        first = next(i for i, r in enumerate(part) if int(r["as_count"]))
        part = part[first:]
        lows = [int(r["bin_low_inclusive"]) for r in part]
        highs = [int(r["bin_high_exclusive"]) for r in part]
        counts = [int(r["as_count"]) for r in part]
        total = int(part[0]["total_origin_as_count"])
        fig, ax = plt.subplots(figsize=(9, 4.8))
        ax.bar(lows, counts, width=[(h - lo) * 0.92 for lo, h in zip(lows, highs)], align="edge", color=BLUE)
        ax.set_xscale("log", base=2)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Number of origin ASes (log scale)")
        ax.set_yscale("log")
        ax.set_ylim(0.8, max(counts) * 3)
        ax.yaxis.set_major_formatter(thousands)
        if quantity == "unique_address_count":
            for prefix_len in (24, 16, 8):
                size = 2 ** (32 - prefix_len)
                ax.axvline(size, color=MUTED, linewidth=1, linestyle="--")
                ax.text(size * 1.1, max(counts) * 2.5, f"= one /{prefix_len}", color=MUTED, fontsize=8, va="top")
        ax.set_title(f"{title}\n(n = {total:,} origin ASes, Nov 10 2025 RouteViews; bin [2^k, 2^(k+1)))")
        ax.grid(axis="x", visible=False)
        save(fig, name)


def graph5() -> None:
    data = rows("task4b.csv")
    classes = list(dict.fromkeys(r["business_label"] for r in data))
    roles = list(dict.fromkeys(r["structural_role"] for r in data))
    fig, ax = plt.subplots(figsize=(9, 4.6))
    left = [0.0] * len(classes)
    for role, color in zip(roles, (BLUE, ORANGE, AQUA)):
        values = [float(next(r["percent"] for r in data if r["business_label"] == c and r["structural_role"] == role))
                  for c in classes]
        bars = ax.barh(classes, values, left=left, color=color, label=role, height=0.6,
                       edgecolor=SURFACE, linewidth=2)
        for bar, value in zip(bars, values):
            if value >= 6:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_height() / 2, f"{value:.1f}%",
                        ha="center", va="center", color="white", fontsize=9, fontweight="bold")
        left = [a + b for a, b in zip(left, values)]
    denominators = {r["business_label"]: int(r["matched_business_class_count"]) for r in data}
    ax.set_yticks(range(len(classes)), [f"{c}\n(n = {denominators[c]:,})" for c in classes])
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Percent of matched ASes in the business class")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3)
    ax.set_title(f"Graph 5: Structural role (Nov 2024 graph) by business class (Apr 2021)\n"
                 f"matched ASes n = {sum(denominators.values()):,}")
    save(fig, "graph5_roles_by_business_class.png")


def graph6() -> None:
    data = rows("task5c.csv")
    ranks = [int(r["cone_rank"]) for r in data]
    cones = [int(r["customer_cone_size"]) for r in data]
    degree = [int(r["global_degree"]) for r in data]
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": (3, 2)})
    top.bar(ranks, cones, color=BLUE, width=0.8)
    top.set_ylabel("Customer-cone size |C(i)| (ASes)")
    top.yaxis.set_major_formatter(thousands)
    top.set_title("Graph 6: Customer-cone size of the top 100 ASes by cone (Nov 2024), "
                  "with each AS's global degree below")
    bottom.bar(ranks, degree, color=ORANGE, width=0.8)
    bottom.set_ylabel("Global degree (neighbors)")
    bottom.yaxis.set_major_formatter(thousands)
    bottom.set_xlabel("Customer-cone rank (1 = largest cone)")
    for ax in (top, bottom):
        ax.grid(axis="x", visible=False)
    save(fig, "graph6_customer_cones.png")


def graph_task6() -> None:
    data = rows("task6.csv")
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for strategy, color, marker, label in (("random", BLUE, "o", "Random removal (mean of 20 seeds, min–max bars)"),
                                           ("targeted", ORANGE, "s", "Targeted removal (highest degree first)")):
        part = [r for r in data if r["strategy"] == strategy]
        f = [100 * float(r["removal_fraction"]) for r in part]
        mean = [float(r["mean_R_crude"]) for r in part]
        low = [m - float(r["min_R_crude"]) for m, r in zip(mean, part)]
        high = [float(r["max_R_crude"]) - m for m, r in zip(mean, part)]
        ax.errorbar(f, mean, yerr=[low, high], color=color, marker=marker, markersize=7, linewidth=2,
                    capsize=4, label=label)
        for x, y in zip(f, mean):
            ax.annotate(f"{y:.3f}", (x, y), xytext=(6, 4), textcoords="offset points", fontsize=8)
    ax.set_xticks([0, 1, 2, 5, 10])
    ax.set_xlabel("Fraction of ASes removed, f (% of all graph ASes)")
    ax.set_ylabel("R(f) = surviving ASes with degree > 0 / surviving ASes")
    ax.set_ylim(0, 1.05)
    ax.legend(loc="lower left")
    ax.set_title("Task 6: Structural robustness of the Nov 2024 AS graph")
    save(fig, "graph_task6_robustness.png")


def main() -> None:
    graph1()
    graph2()
    graph3()
    graph4()
    graph5()
    graph6()
    graph_task6()


if __name__ == "__main__":
    main()
