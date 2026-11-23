# Project 2 data handling

These choices apply to the analyses in [Project_2_2026.pdf](Project_2_2026.pdf). The counts below come from checking the supplied snapshots against the rules in this file. CAIDA classifications and relationships are inferred from available observations, which may omit ASes, links, and routes.

## Input snapshots

| Local file | Snapshot | Use |
| --- | --- | --- |
| `20150801.as2types.txt` | August 1, 2015 | Historical AS business classifications. The header is dated August 2 and references the August 1 snapshot. |
| `20210401.as2types.txt` | April 1, 2021 | AS business classifications for the yearly comparison and the structural-role join. |
| `20241101.as-rel2.txt` | November 1, 2024 | Inferred AS relationships and graph population. |
| `routeviews-rv2-20251110-1200.pfx2as` | November 10, 2025, 12:00 UTC | Observed IPv4 prefix-to-origin-AS associations. |
| `20251001.as-org2info1.txt` | October 2025 | Organization names for AS table entries. |

The table uses the filenames present in this directory. Task 4 specifies the 2021 classification and gives the 2015 filename in parentheses. Use `20210401.as2types.txt` for Task 4 to match the stated year.

## Preprocessing and graph construction

- Skip blank lines and lines beginning with `#` after trimming whitespace. In the organization file, use its `# format` markers to identify the two sections. Strip surrounding whitespace from fields and deduplicate identical records within each file and section.
- Exclude rows with the wrong field count, missing required values, or invalid values in fields used for analysis. Parse ASNs as positive decimal integers in the 32-bit range. Record exclusion counts by input and reason. For classifications, require a source and one of `Transit/Access`, `Content`, or `Enterprise`. Count an ASN once per year when its valid records agree on the label. Exclude and count ASNs with conflicting labels within a snapshot.
- Parse relationships as `AS1|AS2|relationship|source`, with a populated source field. For `-1`, create an edge from provider `AS1` to customer `AS2`. For `0`, treat the endpoints as symmetric peers. Ignore source when constructing edges. Group records by unordered AS pair and collapse equivalent relationships, including reversed peer listings. If valid records disagree on relationship type or provider direction, exclude and count the conflicting pair. Include endpoints of valid relationship records in the graph population and omit self-links from all graph measures.
- Use the directed provider-to-customer graph for hierarchy and customer cones. Use a simple undirected graph containing both relationship types for global degree, connectivity, and clique analysis. Keep the retained relationship type and provider direction when counting distinct customers, peers, and providers. Verify that their sum equals global degree for every graph AS.
- For organization names, join the ASN and organization sections by `org_id`. Require a source and organization ID in both sections, a valid ASN in the ASN section, and a nonempty name in the organization section. Treat unresolved or ambiguous names as unavailable and keep those ASes in ranked tables.

## IPv4 prefix attribution and counting

- Require three tab-separated fields containing an IPv4 network address, a prefix length from 0 to 32, and a valid origin field. Skip non-IPv4 rows and malformed rows, including prefixes with host bits set and origin fields with missing or invalid ASNs.
- Read `_` as the separator between observed origins and `,` as the separator between members of an AS set. Attribute the full prefix to every listed ASN, including all members of any AS set. Deduplicate by `(network prefix, ASN)` for per-AS counts and by network prefix across all ASes for global calculations. These associations describe observed announcements. Address allocation and ownership are outside the scope of the mappings. [CAIDA prefix-to-AS format](https://publicdata.caida.org/datasets/routing/routeviews-prefix2as/README.txt)
- Count distinct prefixes per AS even when they overlap. For address counts, convert each IPv4 prefix to an inclusive integer range, merge overlapping or adjacent ranges, and sum `end - start + 1` across the merged ranges. Apply the same union rule to the distinct prefixes across all ASes for any global address-space total. Summing per-AS address counts can count shared space multiple times.
- A check with `192.0.2.0/24`, its nested `192.0.2.128/25`, a second copy of `192.0.2.0/24`, and the disjoint `198.51.100.0/25` gives three distinct prefixes and 384 distinct addresses.

## Populations, joins, and denominators

| Population | Unique ASNs | Use in reported percentages and distributions |
| --- | ---: | --- |
| ASes with a valid 2015 business label | 51,507 | Each 2015 category share uses the full 2015 classified population. |
| ASes with a valid 2021 business label | 71,665 | Each 2021 category share uses the full 2021 classified population. |
| ASes in valid 2024 relationship records | 77,344 | Degree distributions and the global-degree CCDF use the full graph population. The CCDF is displayed for thresholds of at least 1. |
| ASes with at least one retained IPv4 prefix association | 77,398 | Per-AS prefix and address-space distributions use the full observed IPv4 origin population. |

- **Task 4.** The intersection of the 2021 classification and 2024 graph populations contains 62,897 ASes. There are 8,768 classification-only ASes and 14,447 graph-only ASes. Each structural-role percentage uses the number of matched ASes in its business category as the denominator.
- **Tasks 5 and 7.** The 2024 graph and the set of ASes with a resolved organization name intersect at 76,379 ASes. The remaining 965 graph ASes have no resolved name. Rank ASes using the graph and report how many entries in each ranked table have a matched organization name.
- **Task 6.** The removal fraction uses all original graph ASes as the denominator. At each removal fraction, divide the number of surviving ASes with positive residual degree, the approximation specified in the assignment, by the total number of survivors, including isolated ASes.
- For any additional cross-dataset analysis, use the intersection of the relevant ASN populations and report its size. State the denominator alongside every reported percentage.

## Input audit

The supplied classification, relationship, and prefix files contained zero malformed data rows and zero identical duplicate records. There were zero conflicting business labels within either snapshot, zero self-links or conflicting relationship pairs, and zero repeated normalized prefix-to-AS associations. The relationship graph retained 700,774 distinct AS pairs. The prefix file contained 1,075,992 distinct IPv4 prefixes. The organization file contained 4,826 records with blank organization names, which were excluded from the name lookup.

## Task data exports

Each task script creates the project-local `outputs/` directory if needed. Name subpart exports `outputs/taskNX.csv`, where `N` is the task number and `X` is the lowercase subpart letter. Rerunning a task replaces its CSV files.

Run `python3 task1.py` from the project directory to write `outputs/task1.csv`. The file contains one row per business category. The script prints the input audit for each year to standard error. Each share uses that year's total number of uniquely classified ASes. Changes are 2021 values minus 2015 values. Share changes are expressed in percentage points and calculated before rounding. [CAIDA AS Classification Dataset](https://www.caida.org/catalog/datasets/as-classification/)

Run `python3 task2.py` to write the four files below. The script reports input exclusions and degree-identity violations to standard error. [CAIDA AS Relationships Dataset](https://www.caida.org/catalog/datasets/as-relationships/)

| File | Contents |
| --- | --- |
| `outputs/task2a.csv` | Global, direct-customer, peer, and provider degrees and the degree identity check for every AS. |
| `outputs/task2b.csv` | AS counts for each of the seven histogram bins and each of the four degree types. |
| `outputs/task2c.csv` | A summary row with mean, median, nearest-rank 95th percentile, and maximum global degree, followed by one CCDF row per integer threshold from 1 to the maximum. Each probability divides the number of ASes meeting the threshold by the full graph population, including any zero-degree ASes. |
| `outputs/task2d.csv` | The top ten ASes by global degree with all four degrees. Ties are broken by ascending ASN. |

Run `python3 task4.py` to join the April 2021 business classifications with the November 2024 relationship graph. Assign each graph AS one structural role in priority order based on positive customer degree, then positive peer degree, then neither. The script prints preprocessing counts to standard error.

| File | Contents |
| --- | --- |
| `outputs/task4a.csv` | The 3 × 3 contingency table with business-class totals, the matched sample size and role totals, and counts appearing only in each input population. |
| `outputs/task4b.csv` | Nine business-label and structural-role combinations with counts, matched business-class denominators, and percentages. A zero denominator produces a blank percentage. |
| `outputs/task4c.csv` | All matched ASes in ascending ASN order with both snapshot dates, both labels, and the four degree counts. |

Run `python3 task3.py` to compute per-origin-AS prefix and address counts. The script runs the union correctness checks (the example above, adjacent ranges, and a /0) before reading the data, then cross-checks the global address union against `ipaddress.collapse_addresses`. Address-count rank is the AS's position when sorted by unique addresses.

| File | Contents |
| --- | --- |
| `outputs/task3a.csv` | Distinct prefixes `P_i`, unique addresses `A_i`, and both ranks for every origin AS. |
| `outputs/task3b.csv` | Power-of-two bins `[2^k, 2^(k+1))` for `P_i` and `A_i`, with counts and percentages of all origin ASes. |
| `outputs/task3c_*.csv` | Top 25 ASes by prefix count, top 25 by address count, and the 25 ASes with at least 500 prefixes and the fewest addresses per prefix. |

Run `python3 task5.py` to compute customer cones by breadth-first search over provider-to-customer edges from each AS. A visited set counts each downstream AS once and stops the search from looping on a cycle. Kahn's algorithm counts ASes on or below a p2c cycle; the November 2024 graph has none. `task5a.csv` lists every AS, `task5b.csv` the top 15 by cone size (Table 1), and `task5c.csv` the top 100 by cone size. `task5c_top_by_degree.csv` lists the top 100 by global degree for comparing the two rankings. Ties are broken by ascending ASN.

Run `python3 task6.py` to compare random and degree-targeted removal at f = 0, 1, 2, 5, and 10 percent. Each fraction removes `round(f × 77,344)` ASes. Targeted removal uses the original global degree, with ties broken by ascending ASN. Random removal uses 20 trials seeded 0–19. `task6.csv` reports the mean, standard deviation, minimum, and maximum of R(f) under the assignment's approximation, and the mean exact LCC fraction from union-find for comparison. `task6_trials.csv` has every trial.

Run `python3 task7.py` to run the greedy clique heuristic. The strict version stops at the first ranked AS that is not adjacent to every clique member. The extended version follows the assignment note: it skips such ASes and scans the top 50 ASes by global degree. `task7.csv` lists the extended clique in the order members were added, `task7_scan.csv` records the decision for each of the 50 scanned ASes, and `task7_summary.csv` gives both clique sizes.

Run `python3 make_graphs.py` after the task scripts to render Graphs 1–6 and the Task 6 robustness plot from the CSVs into `outputs/*.png`. Tasks 3, 5, and 7 read organization names through `as_org.py`.

AI assisted in checking the input files, drafting this README, implementing and verifying all task data exports, and producing the graphs.
