"""Write the Task 1 classification statistics to outputs/task1.csv."""

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory


CATEGORIES = ("Transit/Access", "Content", "Enterprise")
PROJECT_DIR = Path(__file__).resolve().parent


def read_classifications(path: Path) -> dict[int, str]:
    """Return one business label per ASN when its valid rows agree."""
    labels_by_asn: dict[int, set[str]] = defaultdict(set)
    seen_records: set[tuple[str, ...]] = set()
    audit: Counter[str] = Counter()

    with path.open(encoding="utf-8") as snapshot:
        for line in snapshot:
            line = line.strip()
            if not line or line.startswith("#"):
                audit["blank or comment lines"] += 1
                continue

            fields = tuple(field.strip() for field in line.split("|"))
            if fields in seen_records:
                audit["duplicate records"] += 1
                continue
            seen_records.add(fields)

            if len(fields) != 3 or not all(fields):
                audit["incomplete or wrong field count"] += 1
                continue

            raw_asn, _, label = fields
            digits = raw_asn.lstrip("0")
            if not (raw_asn.isascii() and raw_asn.isdecimal() and 1 <= len(digits) <= 10):
                audit["invalid ASN"] += 1
                continue
            asn = int(digits)
            if asn >= 2**32:
                audit["invalid ASN"] += 1
                continue
            if label not in CATEGORIES:
                audit["invalid label"] += 1
                continue

            labels_by_asn[asn].add(label)

    classifications = {}
    for asn, labels in labels_by_asn.items():
        if len(labels) == 1:
            classifications[asn] = next(iter(labels))
        else:
            audit["conflicting ASNs"] += 1

    reasons = (
        "blank or comment lines",
        "duplicate records",
        "incomplete or wrong field count",
        "invalid ASN",
        "invalid label",
        "conflicting ASNs",
    )
    print(path.name, "|", ", ".join(f"{reason}={audit[reason]}" for reason in reasons), file=sys.stderr)
    if not classifications:
        raise SystemExit(f"{path.name} contains no ASNs with a valid, consistent classification")
    return classifications


def read_counts(path: Path) -> Counter[str]:
    """Count ASNs with a valid, consistent label by business category."""
    return Counter(read_classifications(path).values())


def main() -> None:
    counts_2015 = read_counts(PROJECT_DIR / "20150801.as2types.txt")
    counts_2021 = read_counts(PROJECT_DIR / "20210401.as2types.txt")
    total_2015 = sum(counts_2015.values())
    total_2021 = sum(counts_2021.values())

    header = (
        "category",
        "2015_count", "2015_total_classified", "2015_share_percent",
        "2021_count", "2021_total_classified", "2021_share_percent",
        "count_change_2021_minus_2015", "share_change_percentage_points_2021_minus_2015",
    )
    rows = []
    for category in CATEGORIES:
        count_2015 = counts_2015[category]
        count_2021 = counts_2021[category]
        share_2015 = 100 * count_2015 / total_2015
        share_2021 = 100 * count_2021 / total_2021
        rows.append((
            category,
            count_2015, total_2015, f"{share_2015:.6f}",
            count_2021, total_2021, f"{share_2021:.6f}",
            count_2021 - count_2015, f"{share_2021 - share_2015:.6f}",
        ))

    output_dir = PROJECT_DIR / "outputs"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "task1.csv"
    with TemporaryDirectory(dir=output_dir) as temporary_dir:
        temporary_path = Path(temporary_dir) / output_path.name
        with temporary_path.open("w", encoding="utf-8", newline="") as output:
            writer = csv.writer(output, lineterminator="\n")
            writer.writerow(header)
            writer.writerows(rows)
        temporary_path.replace(output_path)


if __name__ == "__main__":
    main()
