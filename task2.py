"""Export the four Task 2 datasets to outputs/task2a.csv through task2d.csv."""

import csv
import sys
from bisect import bisect_left
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory


PROJECT_DIR = Path(__file__).resolve().parent
DEGREE_FIELDS = ("global_degree", "customer_degree", "peer_degree", "provider_degree")
HISTOGRAM_FIELDS = ("global_as_count", "customer_as_count", "peer_as_count", "provider_as_count")
BIN_UPPER_BOUNDS = (0, 1, 5, 100, 500, 1000)
BIN_LABELS = ("0", "1", "2-5", "6-100", "101-500", "501-1000", ">1000")


def parse_asn(value: str) -> int:
    digits = value.lstrip("0")
    if not (value.isascii() and value.isdecimal() and 1 <= len(digits) <= 10):
        raise ValueError("Expected a positive decimal ASN")
    asn = int(digits)
    if asn >= 2**32:
        raise ValueError("ASN exceeds the unsigned 32-bit range")
    return asn


def read_relationships(path: Path) -> tuple[set[int], dict[tuple[int, int], int]]:
    """Read valid ASNs and retain exactly one consistent relationship per AS pair."""
    asns: set[int] = set()
    pair_relationships: dict[tuple[int, int], set[int]] = defaultdict(set)
    seen_rows: set[str] = set()
    audit: Counter[str] = Counter()

    with path.open(encoding="utf-8") as source:
        for line in source:
            line = line.strip()
            if not line or line.startswith("#"):
                audit["blank or comment lines"] += 1
                continue

            fields = [field.strip() for field in line.split("|")]
            record = "|".join(fields)
            if record in seen_rows:
                audit["duplicate records"] += 1
                continue
            seen_rows.add(record)

            if len(fields) != 4 or not all(fields):
                audit["incomplete or wrong field count"] += 1
                continue
            first, second, kind, _ = fields
            try:
                first_asn, second_asn = parse_asn(first), parse_asn(second)
            except ValueError:
                audit["invalid ASN"] += 1
                continue
            if kind not in {"-1", "0"}:
                audit["invalid relationship"] += 1
                continue

            asns.update((first_asn, second_asn))
            if first_asn == second_asn:
                audit["self links"] += 1
                continue

            # For a sorted pair, -1 points from low to high and +1 from high to low.
            relationship = int(kind)
            if first_asn > second_asn:
                first_asn, second_asn = second_asn, first_asn
                relationship = -relationship
            evidence = pair_relationships[(first_asn, second_asn)]
            if relationship in evidence:
                audit["equivalent edges"] += 1
            evidence.add(relationship)

    edges = {}
    for pair, evidence in pair_relationships.items():
        if len(evidence) == 1:
            edges[pair] = next(iter(evidence))
        else:
            audit["conflicting pairs"] += 1

    reasons = (
        "blank or comment lines", "duplicate records", "incomplete or wrong field count",
        "invalid ASN", "invalid relationship", "self links", "equivalent edges", "conflicting pairs",
    )
    print(path.name, "|", ", ".join(f"{reason}={audit[reason]}" for reason in reasons), file=sys.stderr)
    return asns, edges


def count_degrees(
    asns: set[int], edges: dict[tuple[int, int], int]
) -> dict[int, tuple[int, int, int, int]]:
    neighbors: Counter[int] = Counter()
    customers: Counter[int] = Counter()
    peers: Counter[int] = Counter()
    providers: Counter[int] = Counter()

    for (low, high), kind in edges.items():
        neighbors.update((low, high))
        if kind == 0:
            peers.update((low, high))
        else:
            provider, customer = (low, high) if kind == -1 else (high, low)
            customers[provider] += 1
            providers[customer] += 1

    return {asn: (neighbors[asn], customers[asn], peers[asn], providers[asn]) for asn in asns}


def write_csv(path: Path, header: tuple[str, ...], rows: Iterable[tuple[object, ...]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def ccdf_rows(sorted_degrees: list[int]) -> Iterable[tuple[object, ...]]:
    """Yield one summary row followed by Pr(D >= k) for each positive threshold."""
    total = len(sorted_degrees)
    frequencies = Counter(sorted_degrees)
    maximum = sorted_degrees[-1]
    percentile_rank = (95 * total + 99) // 100  # Nearest-rank percentile, ceil(0.95 * total).
    yield (
        "summary", "", "", total, "",
        sum(sorted_degrees) / total, median(sorted_degrees),
        sorted_degrees[percentile_rank - 1], maximum,
    )

    at_least_threshold = total
    for threshold in range(1, maximum + 1):
        at_least_threshold -= frequencies[threshold - 1]
        yield ("ccdf", threshold, at_least_threshold, total, at_least_threshold / total, "", "", "", "")


def main() -> None:
    asns, edges = read_relationships(PROJECT_DIR / "20241101.as-rel2.txt")
    if not asns:
        raise SystemExit("The relationship snapshot contains no valid ASNs")
    degrees = count_degrees(asns, edges)
    violations = {
        asn for asn, (global_degree, customers, peers, providers) in degrees.items()
        if global_degree != customers + peers + providers
    }
    print(f"ASNs={len(asns)}, edges={len(edges)}, degree identity violations={len(violations)}", file=sys.stderr)
    if violations:
        examples = [(asn, degrees[asn]) for asn in sorted(violations)[:10]]
        raise SystemExit(f"Degree identity failed for ASNs with degrees {examples}")

    histogram = [[0] * len(DEGREE_FIELDS) for _ in BIN_LABELS]
    for values in degrees.values():
        for column, degree in enumerate(values):
            histogram[bisect_left(BIN_UPPER_BOUNDS, degree)][column] += 1
    global_degrees = sorted(values[0] for values in degrees.values())
    top_asns = sorted(degrees, key=lambda asn: (-degrees[asn][0], asn))[:10]

    output_dir = PROJECT_DIR / "outputs"
    output_dir.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=output_dir) as temporary_dir:
        staging = Path(temporary_dir)
        write_csv(
            staging / "task2a.csv",
            ("asn", *DEGREE_FIELDS, "degree_identity_holds"),
            ((asn, *degrees[asn], asn not in violations) for asn in sorted(degrees)),
        )
        write_csv(
            staging / "task2b.csv",
            ("degree_bin", *HISTOGRAM_FIELDS),
            ((label, *counts) for label, counts in zip(BIN_LABELS, histogram)),
        )
        write_csv(
            staging / "task2c.csv",
            ("record_type", "degree_threshold", "as_count_at_least_threshold", "total_as_count", "ccdf",
             "mean_global_degree", "median_global_degree", "p95_global_degree", "max_global_degree"),
            ccdf_rows(global_degrees),
        )
        write_csv(
            staging / "task2d.csv",
            ("rank", "asn", *DEGREE_FIELDS),
            ((rank, asn, *degrees[asn]) for rank, asn in enumerate(top_asns, start=1)),
        )
        for csv_path in sorted(staging.iterdir()):
            csv_path.replace(output_dir / csv_path.name)


if __name__ == "__main__":
    main()
