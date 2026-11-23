"""Export the Task 6 robustness results (random vs. degree-targeted AS removal) to outputs/task6*.csv."""

import sys
from pathlib import Path
from statistics import mean, pstdev
from tempfile import TemporaryDirectory

import numpy as np

from task2 import count_degrees, read_relationships, write_csv


PROJECT_DIR = Path(__file__).resolve().parent
FRACTIONS = (0.0, 0.01, 0.02, 0.05, 0.10)
TRIALS = 20


def largest_component(node_count: int, src: np.ndarray, dst: np.ndarray) -> int:
    """Size of the true largest connected component (union-find), counting only nodes with an edge."""
    parent = list(range(node_count))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in zip(src.tolist(), dst.tolist()):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    touched = np.unique(np.concatenate((src, dst)))
    if touched.size == 0:
        return 1 if node_count else 0
    roots = np.fromiter((find(int(x)) for x in touched), dtype=np.int64, count=touched.size)
    return int(np.bincount(roots).max())


def evaluate(removed: np.ndarray, src: np.ndarray, dst: np.ndarray) -> tuple[int, int, float, float]:
    """Return survivors, crude-LCC count, crude R(f), and exact R(f) for a removal mask."""
    node_count = removed.size
    alive_edges = ~(removed[src] | removed[dst])
    s, d = src[alive_edges], dst[alive_edges]
    survivors = int(node_count - removed.sum())
    residual = np.bincount(s, minlength=node_count) + np.bincount(d, minlength=node_count)
    crude = int(((residual > 0) & ~removed).sum())
    exact = largest_component(node_count, s, d)
    return survivors, crude, crude / survivors, exact / survivors


def main() -> None:
    asns, edges = read_relationships(PROJECT_DIR / "20241101.as-rel2.txt")
    degrees = count_degrees(asns, edges)
    order = sorted(asns)
    index = {asn: i for i, asn in enumerate(order)}
    src = np.array([index[a] for a, _ in edges], dtype=np.int64)
    dst = np.array([index[b] for _, b in edges], dtype=np.int64)
    n = len(order)
    # Targeted order uses the original global degree (before any removal); ties by ascending ASN.
    targeted_order = np.array([index[a] for a in sorted(asns, key=lambda a: (-degrees[a][0], a))])

    trial_rows, summary_rows = [], []
    for f in FRACTIONS:
        k = round(f * n)
        removed = np.zeros(n, dtype=bool)
        removed[targeted_order[:k]] = True
        survivors, crude, r_crude, r_exact = evaluate(removed, src, dst)
        trial_rows.append(("targeted", f, "", k, survivors, crude, f"{r_crude:.6f}", f"{r_exact:.6f}"))
        summary_rows.append(("targeted", f, k, 1, f"{r_crude:.6f}", "0", f"{r_crude:.6f}", f"{r_crude:.6f}",
                             f"{r_exact:.6f}"))

        crude_values, exact_values = [], []
        for seed in range(TRIALS):
            rng = np.random.default_rng(seed)
            removed = np.zeros(n, dtype=bool)
            removed[rng.choice(n, size=k, replace=False)] = True
            survivors, crude, r_crude, r_exact = evaluate(removed, src, dst)
            crude_values.append(r_crude)
            exact_values.append(r_exact)
            trial_rows.append(("random", f, seed, k, survivors, crude, f"{r_crude:.6f}", f"{r_exact:.6f}"))
        summary_rows.append(("random", f, k, TRIALS, f"{mean(crude_values):.6f}", f"{pstdev(crude_values):.6f}",
                             f"{min(crude_values):.6f}", f"{max(crude_values):.6f}", f"{mean(exact_values):.6f}"))
        print(f"f={f}: removed={k}, targeted R={summary_rows[-2][4]}, random mean R={summary_rows[-1][4]}",
              file=sys.stderr)

    output_dir = PROJECT_DIR / "outputs"
    output_dir.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=output_dir) as temporary_dir:
        staging = Path(temporary_dir)
        write_csv(staging / "task6.csv",
                  ("strategy", "removal_fraction", "removed_as_count", "trials", "mean_R_crude", "std_R_crude",
                   "min_R_crude", "max_R_crude", "mean_R_exact_lcc"),
                  summary_rows)
        write_csv(staging / "task6_trials.csv",
                  ("strategy", "removal_fraction", "seed", "removed_as_count", "surviving_as_count",
                   "surviving_with_positive_degree", "R_crude", "R_exact_lcc"),
                  trial_rows)
        for csv_path in sorted(staging.iterdir()):
            csv_path.replace(output_dir / csv_path.name)


if __name__ == "__main__":
    main()
