#!/usr/bin/env python3
"""Generate hgnc.tsv, input.tsv and the gold mapping.tsv for id-mapping.

Curated, hand-chosen gene set with real HGNC-approved symbols, a few
well-known previous/alias symbols, and deliberately-garbled queries
that must resolve to ``not_found``. All deterministic: no RNG.
"""
from __future__ import annotations

import csv
from pathlib import Path

DATA = Path("/out/data")
GOLD = Path("/out/gold")

# (hgnc_id, current_symbol, aliases, ensembl_gene_id)
HGNC_ROWS = [
    ("HGNC:11998", "TP53",    "P53",                   "ENSG00000141510"),
    ("HGNC:1097",  "BRAF",    "",                      "ENSG00000157764"),
    ("HGNC:1100",  "BRCA1",   "RNF53|PPP1R53",         "ENSG00000012048"),
    ("HGNC:1101",  "BRCA2",   "FANCD1",                "ENSG00000139618"),
    ("HGNC:6407",  "KRAS",    "KRAS2|NS3|RASK2",       "ENSG00000133703"),
    ("HGNC:7989",  "NRAS",    "N-RAS|NS6",             "ENSG00000213281"),
    ("HGNC:3236",  "EGFR",    "ERBB|ERBB1|HER1",       "ENSG00000146648"),
    ("HGNC:3430",  "ERBB2",   "HER2|NEU|NGL",          "ENSG00000141736"),
    ("HGNC:9588",  "PTEN",    "MMAC1|TEP1",            "ENSG00000171862"),
    ("HGNC:8975",  "PIK3CA",  "",                      "ENSG00000121879"),
    ("HGNC:583",   "APC",     "DP2|DP3",               "ENSG00000134982"),
    ("HGNC:7132",  "MYC",     "C-MYC|MYCC",            "ENSG00000136997"),
    ("HGNC:6407",  "CDKN2A",  "P16|INK4A|MTS1",        "ENSG00000147889"),
    ("HGNC:9884",  "RB1",     "RB|OSRC",               "ENSG00000139687"),
    ("HGNC:10471", "SMAD4",   "DPC4|MADH4",            "ENSG00000141646"),
    ("HGNC:2514",  "CTNNB1",  "",                      "ENSG00000168036"),
    ("HGNC:11730", "TERT",    "TP2|TRT|EST2",          "ENSG00000164362"),
    ("HGNC:5973",  "IDH1",    "PICD",                  "ENSG00000138413"),
    ("HGNC:5383",  "HRAS",    "HRAS1|RASH1",           "ENSG00000174775"),
    ("HGNC:7989",  "MET",     "HGFR|RCCP2",            "ENSG00000105976"),
]

QUERIES = [
    "TP53",       # exact
    "P53",        # alias -> TP53
    "BRAF",       # exact
    "BRCA1",      # exact
    "RNF53",      # alias -> BRCA1
    "FANCD1",     # alias -> BRCA2
    "KRAS2",      # alias -> KRAS
    "N-RAS",      # alias -> NRAS
    "HER1",       # alias -> EGFR
    "HER2",       # alias -> ERBB2
    "PTEN",       # exact
    "PIK3CA",     # exact
    "MMAC1",      # alias -> PTEN
    "C-MYC",      # alias -> MYC
    "P16",        # alias -> CDKN2A
    "RB1",        # exact
    "DPC4",       # alias -> SMAD4
    "TERT",       # exact
    "HGFR",       # alias -> MET
    "NOTCH1",     # not_found
    "xyzzy",      # not_found
    "BRCA3",      # not_found (doesn't exist)
    "tp53",       # not_found (case-sensitive)
    "ERBB1",      # alias -> EGFR
    "MYCC",       # alias -> MYC
]


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    GOLD.mkdir(parents=True, exist_ok=True)

    with (DATA / "hgnc.tsv").open("w") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["hgnc_id", "symbol", "aliases", "ensembl_gene_id"])
        for row in HGNC_ROWS:
            w.writerow(row)

    with (DATA / "input.tsv").open("w") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["query_symbol"])
        for q in QUERIES:
            w.writerow([q])

    current = {r[1]: r for r in HGNC_ROWS}
    alias_to_row = {}
    for r in HGNC_ROWS:
        aliases = r[2].split("|") if r[2] else []
        for a in aliases:
            if a:
                alias_to_row[a] = r

    sorted_queries = sorted(QUERIES)
    with (GOLD / "mapping.tsv").open("w") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["query_symbol", "resolved_symbol", "ensembl_gene_id", "status"])
        for q in sorted_queries:
            if q in current:
                r = current[q]
                w.writerow([q, r[1], r[3], "exact"])
            elif q in alias_to_row:
                r = alias_to_row[q]
                w.writerow([q, r[1], r[3], "alias"])
            else:
                w.writerow([q, "", "", "not_found"])

    print(f"wrote hgnc.tsv ({len(HGNC_ROWS)} rows), "
          f"input.tsv ({len(QUERIES)} queries), gold mapping.tsv")


if __name__ == "__main__":
    main()
