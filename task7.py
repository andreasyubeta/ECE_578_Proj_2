"""Export the Task 7 greedy-clique (candidate Tier-1) results to outputs/task7*.csv."""

import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from tempfile import TemporaryDirectory

from as_org import read_org_names
from task2 import count_degrees, read_relationships, write_csv


PROJECT_DIR = Path(__file__).resolve().parent
SEARCH_DEPTH = 50


def main() -> None:
    asns, edges = read_relationships(PROJECT_DIR / "20241101.as-rel2.txt")
    degrees = count_degrees(asns, edges)
    neighbors: dict[int, set[int]] = defaultdict(set)
    for low, high in edges:  # Any link type counts.
        neighbors[low].add(high)
        neighbors[high].add(low)
    org_names = read_org_names()

    ranked = sorted(asns, key=lambda a: (-degrees[a][0], a))

    # Strict heuristic: stop at the first ranked AS not adjacent to every clique member.
    strict: list[int] = []
    for asn in ranked:
        if all(member in neighbors[asn] for member in strict):
            strict.append(asn)
        else:
            stop_at = asn
            break
    print(f"strict greedy clique size={len(strict)}, terminated at AS{stop_at} "
          f"(degree rank {ranked.index(stop_at) + 1})", file=sys.stderr)

    # Extended heuristic from the assignment note: skip non-fitting ASes, scan the top 50.
    clique: list[int] = []
    decisions = []
    for rank, asn in enumerate(ranked[:SEARCH_DEPTH], start=1):
        missing = [member for member in clique if member not in neighbors[asn]]
        if not missing:
            clique.append(asn)
            decisions.append((rank, asn, "added", len(clique), ""))
        else:
            decisions.append((rank, asn, "skipped", "", " ".join(map(str, missing))))
    assert all(b in neighbors[a] for a, b in combinations(clique, 2)), "result is not a clique"
    print(f"extended greedy clique size (top {SEARCH_DEPTH} scanned)={len(clique)}: {clique}", file=sys.stderr)

    def describe(asn: int) -> tuple[object, ...]:
        global_degree, customer_degree, peer_degree, provider_degree = degrees[asn]
        return (asn, org_names.get(asn, ""), global_degree, customer_degree, peer_degree, provider_degree)

    output_dir = PROJECT_DIR / "outputs"
    output_dir.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=output_dir) as temporary_dir:
        staging = Path(temporary_dir)
        write_csv(
            staging / "task7.csv",
            ("order_added", "asn", "organization", "incident_links_global_degree", "customer_degree",
             "peer_degree", "provider_degree", "global_degree_rank"),
            ((i, *describe(asn), ranked.index(asn) + 1) for i, asn in enumerate(clique, start=1)),
        )
        write_csv(
            staging / "task7_scan.csv",
            ("global_degree_rank", "asn", "organization", "global_degree", "decision", "clique_position",
             "not_adjacent_to_clique_members"),
            ((rank, asn, org_names.get(asn, ""), degrees[asn][0], decision, position, missing)
             for rank, asn, decision, position, missing in decisions),
        )
        write_csv(
            staging / "task7_summary.csv",
            ("method", "clique_size", "members"),
            (("strict (stop at first non-fitting AS)", len(strict), " ".join(map(str, strict))),
             (f"extended (skip non-fitting, top {SEARCH_DEPTH} scanned)", len(clique), " ".join(map(str, clique)))),
        )
        for csv_path in sorted(staging.iterdir()):
            csv_path.replace(output_dir / csv_path.name)


if __name__ == "__main__":
    main()
