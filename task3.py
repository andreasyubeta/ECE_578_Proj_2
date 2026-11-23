"""Export the Task 3 per-AS IPv4 prefix and address-space datasets to outputs/task3*.csv."""

import ipaddress
import sys
from collections import Counter, defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

from as_org import read_org_names
from task2 import parse_asn, write_csv


PROJECT_DIR = Path(__file__).resolve().parent
PREFIX_FILE = PROJECT_DIR / "routeviews-rv2-20251110-1200.pfx2as"

Prefix = tuple[int, int]  # (network address as integer, prefix length)


def read_prefixes(path: Path) -> dict[int, set[Prefix]]:
    """Return origin ASN -> set of distinct IPv4 prefixes it was observed originating.

    `_` separates multiple origin ASes (MOAS) and `,` separates members of an AS set.
    Every listed ASN receives the full prefix.
    """
    prefixes_by_asn: dict[int, set[Prefix]] = defaultdict(set)
    seen_rows: set[str] = set()
    audit: Counter[str] = Counter()

    with path.open(encoding="utf-8") as source:
        for line in source:
            line = line.strip()
            if not line or line.startswith("#"):
                audit["blank or comment lines"] += 1
                continue
            fields = [field.strip() for field in line.split("\t")]
            record = "\t".join(fields)
            if record in seen_rows:
                audit["duplicate records"] += 1
                continue
            seen_rows.add(record)
            if len(fields) != 3 or not all(fields):
                audit["incomplete or wrong field count"] += 1
                continue

            address, raw_length, origin = fields
            try:
                length = int(raw_length)
                if not 0 <= length <= 32:
                    raise ValueError
                network = ipaddress.IPv4Network(f"{address}/{length}", strict=True)
            except ValueError:
                audit["non-IPv4 or invalid prefix"] += 1
                continue
            try:
                origins = {parse_asn(asn) for group in origin.split("_") for asn in group.split(",")}
            except ValueError:
                audit["invalid origin"] += 1
                continue

            if "_" in origin:
                audit["multi-origin (MOAS) rows"] += 1
            if "," in origin:
                audit["AS-set rows"] += 1
            prefix = (int(network.network_address), length)
            for asn in origins:
                if prefix in prefixes_by_asn[asn]:
                    audit["repeated (prefix, ASN) associations"] += 1
                prefixes_by_asn[asn].add(prefix)

    print(path.name, "|", ", ".join(f"{k}={v}" for k, v in sorted(audit.items())), file=sys.stderr)
    return prefixes_by_asn


def union_size(prefixes: set[Prefix]) -> int:
    """Count distinct IPv4 addresses covered by the union of the prefixes."""
    ranges = sorted((start, start + (1 << (32 - length)) - 1) for start, length in prefixes)
    total = 0
    current_start, current_end = None, None
    for start, end in ranges:
        if current_end is not None and start <= current_end + 1:
            current_end = max(current_end, end)
            continue
        if current_end is not None:
            total += current_end - current_start + 1
        current_start, current_end = start, end
    if current_end is not None:
        total += current_end - current_start + 1
    return total


def to_prefix(cidr: str) -> Prefix:
    network = ipaddress.IPv4Network(cidr)
    return int(network.network_address), network.prefixlen


def check_union() -> None:
    """Correctness checks for the prefix-union calculation."""
    sample = [to_prefix(c) for c in ("192.0.2.0/24", "192.0.2.128/25", "192.0.2.0/24", "198.51.100.0/25")]
    distinct = set(sample)
    assert len(distinct) == 3 and union_size(distinct) == 384, "nested/duplicate/disjoint check failed"
    adjacent = {to_prefix("10.0.0.0/25"), to_prefix("10.0.0.128/25")}
    assert union_size(adjacent) == 256, "adjacent-range check failed"
    assert union_size({to_prefix("0.0.0.0/0"), to_prefix("8.8.8.0/24")}) == 2**32, "full-space check failed"
    print("union checks passed: nested /25 in /24 + duplicate + disjoint /25 = 384; adjacent /25s = 256; "
          "/0 = 2^32", file=sys.stderr)


def log2_bin(value: int) -> int:
    """Bin index k such that 2^k <= value < 2^(k+1)."""
    return value.bit_length() - 1


def main() -> None:
    check_union()
    prefixes_by_asn = read_prefixes(PREFIX_FILE)
    if not prefixes_by_asn:
        raise SystemExit("The prefix snapshot contains no valid IPv4 associations")

    counts = {asn: (len(prefixes), union_size(prefixes)) for asn, prefixes in prefixes_by_asn.items()}

    # Global cross-check: union over all distinct prefixes, computed two independent ways.
    all_prefixes = set().union(*prefixes_by_asn.values())
    global_union = union_size(all_prefixes)
    collapsed = ipaddress.collapse_addresses(
        ipaddress.IPv4Network((start, length)) for start, length in all_prefixes
    )
    library_union = sum(net.num_addresses for net in collapsed)
    assert global_union == library_union, (global_union, library_union)
    per_as_sum = sum(a for _, a in counts.values())
    print(f"origin ASNs={len(counts)}, distinct prefixes={len(all_prefixes)}, "
          f"(prefix, ASN) associations={sum(p for p, _ in counts.values())}, "
          f"global address union={global_union} ({100 * global_union / 2**32:.2f}% of IPv4; "
          f"matches ipaddress.collapse_addresses), sum of per-AS A_i={per_as_sum}", file=sys.stderr)

    org_names = read_org_names()
    p_rank = {asn: r for r, asn in enumerate(sorted(counts, key=lambda a: (-counts[a][0], a)), start=1)}
    a_rank = {asn: r for r, asn in enumerate(sorted(counts, key=lambda a: (-counts[a][1], a)), start=1)}

    p_bins: Counter[int] = Counter(log2_bin(p) for p, _ in counts.values())
    a_bins: Counter[int] = Counter(log2_bin(a) for _, a in counts.values())
    total = len(counts)

    def summary_row(asn: int) -> tuple[object, ...]:
        p, a = counts[asn]
        return (asn, org_names.get(asn, ""), p, a, f"{a / p:.1f}", p_rank[asn], a_rank[asn])

    by_prefix_count = sorted(counts, key=lambda a: p_rank[a])
    # ASes with many prefixes but little space: P_i >= 500 and lowest addresses per prefix.
    many_small = sorted((a for a in counts if counts[a][0] >= 500), key=lambda a: (counts[a][1] / counts[a][0], a))

    output_dir = PROJECT_DIR / "outputs"
    output_dir.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=output_dir) as temporary_dir:
        staging = Path(temporary_dir)
        write_csv(
            staging / "task3a.csv",
            ("asn", "prefix_count", "unique_address_count", "prefix_count_rank", "address_count_rank"),
            ((asn, *counts[asn], p_rank[asn], a_rank[asn]) for asn in sorted(counts)),
        )
        write_csv(
            staging / "task3b.csv",
            ("quantity", "bin_low_inclusive", "bin_high_exclusive", "as_count", "total_origin_as_count", "percent"),
            [("prefix_count", 2**k, 2**(k + 1), p_bins[k], total, f"{100 * p_bins[k] / total:.6f}")
             for k in range(max(p_bins) + 1)]
            + [("unique_address_count", 2**k, 2**(k + 1), a_bins[k], total, f"{100 * a_bins[k] / total:.6f}")
               for k in range(max(a_bins) + 1)],
        )
        header = ("asn", "organization", "prefix_count", "unique_address_count", "addresses_per_prefix",
                  "prefix_count_rank", "address_count_rank")
        write_csv(staging / "task3c_top_by_prefixes.csv", header, (summary_row(a) for a in by_prefix_count[:25]))
        write_csv(staging / "task3c_many_prefixes_small_space.csv", header,
                  (summary_row(a) for a in many_small[:25]))
        write_csv(staging / "task3c_top_by_addresses.csv", header,
                  (summary_row(a) for a in sorted(counts, key=lambda a: a_rank[a])[:25]))
        for csv_path in sorted(staging.iterdir()):
            csv_path.replace(output_dir / csv_path.name)


if __name__ == "__main__":
    main()
