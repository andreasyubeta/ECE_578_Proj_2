"""Export the Task 5 customer-cone datasets to outputs/task5a.csv through task5c.csv."""

import sys
from collections import defaultdict, deque
from pathlib import Path
from tempfile import TemporaryDirectory

from as_org import read_org_names
from task2 import count_degrees, read_relationships, write_csv


PROJECT_DIR = Path(__file__).resolve().parent


def customer_lists(edges: dict[tuple[int, int], int]) -> dict[int, list[int]]:
    """Provider -> direct customers from the deduplicated p2c edges (peer edges ignored)."""
    customers: dict[int, list[int]] = defaultdict(list)
    for (low, high), kind in edges.items():
        if kind == -1:
            customers[low].append(high)
        elif kind == 1:
            customers[high].append(low)
    return customers


def count_cycle_nodes(asns: set[int], customers: dict[int, list[int]]) -> int:
    """Kahn's algorithm: ASes that are never released lie on, or below, a p2c cycle."""
    in_degree = dict.fromkeys(asns, 0)
    for children in customers.values():
        for child in children:
            in_degree[child] += 1
    queue = deque(asn for asn, d in in_degree.items() if d == 0)
    released = 0
    while queue:
        asn = queue.popleft()
        released += 1
        for child in customers.get(asn, ()):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)
    return len(asns) - released


def cone_size(root: int, customers: dict[int, list[int]]) -> int:
    """|C(root)|: breadth-first search over p2c edges with a visited set.

    Each AS is added to `visited` once, so multiple paths to it are counted once and a
    p2c cycle cannot cause the traversal to revisit nodes or loop forever.
    """
    visited = {root}
    queue = deque((root,))
    while queue:
        for child in customers.get(queue.popleft(), ()):
            if child not in visited:
                visited.add(child)
                queue.append(child)
    return len(visited)


def compute_cones(asns: set[int], edges: dict[tuple[int, int], int]) -> dict[int, int]:
    customers = customer_lists(edges)
    cycle_nodes = count_cycle_nodes(asns, customers)
    print(f"p2c edges={sum(map(len, customers.values()))}, ASes on or below a p2c cycle={cycle_nodes}",
          file=sys.stderr)
    return {asn: cone_size(asn, customers) if asn in customers else 1 for asn in asns}


def main() -> None:
    asns, edges = read_relationships(PROJECT_DIR / "20241101.as-rel2.txt")
    degrees = count_degrees(asns, edges)
    cones = compute_cones(asns, edges)
    org_names = read_org_names()
    print(f"graph ASes with a resolved organization name={len(asns & org_names.keys())} of {len(asns)}",
          file=sys.stderr)

    cone_order = sorted(asns, key=lambda a: (-cones[a], a))
    degree_order = sorted(asns, key=lambda a: (-degrees[a][0], a))
    customer_order = sorted(asns, key=lambda a: (-degrees[a][1], a))
    cone_rank = {asn: r for r, asn in enumerate(cone_order, start=1)}
    degree_rank = {asn: r for r, asn in enumerate(degree_order, start=1)}
    customer_rank = {asn: r for r, asn in enumerate(customer_order, start=1)}

    def row(asn: int) -> tuple[object, ...]:
        global_degree, customer_degree, peer_degree, provider_degree = degrees[asn]
        return (cone_rank[asn], asn, org_names.get(asn, ""), global_degree, customer_degree, peer_degree,
                provider_degree, cones[asn], degree_rank[asn], customer_rank[asn])

    header = ("cone_rank", "asn", "organization", "global_degree", "customer_degree", "peer_degree",
              "provider_degree", "customer_cone_size", "global_degree_rank", "customer_degree_rank")
    top_15 = cone_order[:15]
    top_100 = cone_order[:100]
    print(f"top-15 cone table entries with an organization name={sum(a in org_names for a in top_15)}",
          file=sys.stderr)
    overlap = len(set(top_100) & set(degree_order[:100]))
    print(f"ASes in both the top-100 by cone and top-100 by global degree={overlap}", file=sys.stderr)

    output_dir = PROJECT_DIR / "outputs"
    output_dir.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=output_dir) as temporary_dir:
        staging = Path(temporary_dir)
        write_csv(staging / "task5a.csv", header, (row(asn) for asn in sorted(asns)))
        write_csv(staging / "task5b.csv", header, (row(asn) for asn in top_15))
        write_csv(staging / "task5c.csv", header, (row(asn) for asn in top_100))
        write_csv(staging / "task5c_top_by_degree.csv", header, (row(asn) for asn in degree_order[:100]))
        for csv_path in sorted(staging.iterdir()):
            csv_path.replace(output_dir / csv_path.name)


if __name__ == "__main__":
    main()
