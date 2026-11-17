"""Export the Task 4 contingency table, percentages, and matched AS records."""

from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

from task1 import CATEGORIES, read_classifications
from task2 import DEGREE_FIELDS, count_degrees, read_relationships, write_csv


PROJECT_DIR = Path(__file__).resolve().parent
CLASSIFICATION_DATE = "2021-04-01"
RELATIONSHIP_DATE = "2024-11-01"
CUSTOMER_SERVING = "Customer-serving"
PEERING_EDGE = "Peering edge"
STUB_OR_MULTIHOMED = "Stubs or Multi-homed ASes"
ROLES = (CUSTOMER_SERVING, PEERING_EDGE, STUB_OR_MULTIHOMED)


def structural_role(customer_degree: int, peer_degree: int) -> str:
    if customer_degree > 0:
        return CUSTOMER_SERVING
    if peer_degree > 0:
        return PEERING_EDGE
    return STUB_OR_MULTIHOMED


def main() -> None:
    classifications = read_classifications(PROJECT_DIR / "20210401.as2types.txt")
    graph_asns, edges = read_relationships(PROJECT_DIR / "20241101.as-rel2.txt")
    degrees = count_degrees(graph_asns, edges)
    roles = {asn: structural_role(customers, peers) for asn, (_, customers, peers, _) in degrees.items()}

    matched = sorted(graph_asns.intersection(classifications))
    classification_only = classifications.keys() - graph_asns
    relationship_only = graph_asns.difference(classifications)
    cells = Counter((classifications[asn], roles[asn]) for asn in matched)
    class_totals = Counter(classifications[asn] for asn in matched)
    role_totals = Counter(roles[asn] for asn in matched)

    contingency_rows = [
        ("matched", label, *(cells[label, role] for role in ROLES), class_totals[label])
        for label in CATEGORIES
    ]
    contingency_rows.extend((
        ("matched_total", "", *(role_totals[role] for role in ROLES), len(matched)),
        ("classification_only", "", "", "", "", len(classification_only)),
        ("relationship_only", "", "", "", "", len(relationship_only)),
    ))

    percentage_rows = []
    for label in CATEGORIES:
        denominator = class_totals[label]
        for role in ROLES:
            count = cells[label, role]
            percent = f"{100 * count / denominator:.6f}" if denominator else ""
            percentage_rows.append((label, role, count, denominator, percent))

    output_dir = PROJECT_DIR / "outputs"
    output_dir.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=output_dir) as temporary_dir:
        staging = Path(temporary_dir)
        write_csv(
            staging / "task4a.csv",
            ("population", "business_label", "customer_serving_count", "peering_edge_count",
             "stub_or_multihomed_count", "as_count"),
            contingency_rows,
        )
        write_csv(
            staging / "task4b.csv",
            ("business_label", "structural_role", "as_count", "matched_business_class_count", "percent"),
            percentage_rows,
        )
        write_csv(
            staging / "task4c.csv",
            ("asn", "classification_snapshot", "relationship_snapshot", "business_label", "structural_role",
             *DEGREE_FIELDS),
            ((asn, CLASSIFICATION_DATE, RELATIONSHIP_DATE, classifications[asn], roles[asn], *degrees[asn])
             for asn in matched),
        )
        for csv_path in sorted(staging.iterdir()):
            csv_path.replace(output_dir / csv_path.name)


if __name__ == "__main__":
    main()
