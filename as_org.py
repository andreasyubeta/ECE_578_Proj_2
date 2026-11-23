"""Shared AS-to-organization lookup for Tasks 3, 5, and 7."""

import sys
from collections import Counter, defaultdict
from pathlib import Path

from task2 import parse_asn


PROJECT_DIR = Path(__file__).resolve().parent
ORG_FILE = PROJECT_DIR / "20251001.as-org2info1.txt"


def read_org_names(path: Path = ORG_FILE) -> dict[int, str]:
    """Return ASN -> organization name, joining the ASN and organization sections by org_id.

    Names that cannot be resolved, or that resolve ambiguously (an ASN listed under more
    than one org_id, or an org_id with conflicting names), are left out of the lookup.
    """
    section = None
    org_names: dict[str, set[str]] = defaultdict(set)
    asn_orgs: dict[int, set[str]] = defaultdict(set)
    seen: set[tuple[str | None, str]] = set()
    audit: Counter[str] = Counter()

    with path.open(encoding="utf-8") as source:
        for line in source:
            line = line.strip()
            if line.startswith("# format:"):
                section = "org" if line.startswith("# format:org_id") else "asn"
                continue
            if not line or line.startswith("#"):
                continue
            fields = [field.strip() for field in line.split("|")]
            key = (section, "|".join(fields))
            if key in seen:
                audit["duplicate records"] += 1
                continue
            seen.add(key)

            if section == "org":
                if len(fields) != 5:
                    audit["org rows with wrong field count"] += 1
                    continue
                org_id, _, name, _, source_name = fields
                if not org_id or not source_name:
                    audit["org rows missing id or source"] += 1
                    continue
                if not name:
                    audit["org rows with blank name"] += 1
                    continue
                org_names[org_id].add(name)
            elif section == "asn":
                if len(fields) != 6:
                    audit["asn rows with wrong field count"] += 1
                    continue
                raw_asn, _, _, org_id, _, source_name = fields
                if not org_id or not source_name:
                    audit["asn rows missing org id or source"] += 1
                    continue
                try:
                    asn = parse_asn(raw_asn)
                except ValueError:
                    audit["asn rows with invalid ASN"] += 1
                    continue
                asn_orgs[asn].add(org_id)
            else:
                audit["rows before any format marker"] += 1

    names: dict[int, str] = {}
    for asn, org_ids in asn_orgs.items():
        if len(org_ids) != 1:
            audit["ASNs with multiple org_ids"] += 1
            continue
        candidates = org_names.get(next(iter(org_ids)), set())
        if len(candidates) != 1:
            audit["ASNs with unresolved or ambiguous name"] += 1
            continue
        names[asn] = next(iter(candidates))

    print(path.name, "|", ", ".join(f"{k}={v}" for k, v in sorted(audit.items())),
          f"| resolved ASNs={len(names)}", file=sys.stderr)
    return names
