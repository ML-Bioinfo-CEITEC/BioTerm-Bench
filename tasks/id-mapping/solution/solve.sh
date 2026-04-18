#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
import csv

current = {}
alias_to_row = {}
with open("/app/data/hgnc.tsv") as fh:
    reader = csv.DictReader(fh, delimiter="\t")
    for row in reader:
        current[row["symbol"]] = row
        aliases = row["aliases"].split("|") if row["aliases"] else []
        for a in aliases:
            if a:
                alias_to_row[a] = row

queries = []
with open("/app/data/input.tsv") as fh:
    reader = csv.DictReader(fh, delimiter="\t")
    for row in reader:
        queries.append(row["query_symbol"])

queries.sort()

with open("/app/output/mapping.tsv", "w") as out:
    w = csv.writer(out, delimiter="\t", lineterminator="\n")
    w.writerow(["query_symbol", "resolved_symbol", "ensembl_gene_id", "status"])
    for q in queries:
        if q in current:
            r = current[q]
            w.writerow([q, r["symbol"], r["ensembl_gene_id"], "exact"])
        elif q in alias_to_row:
            r = alias_to_row[q]
            w.writerow([q, r["symbol"], r["ensembl_gene_id"], "alias"])
        else:
            w.writerow([q, "", "", "not_found"])
PY
