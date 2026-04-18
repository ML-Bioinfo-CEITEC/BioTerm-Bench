#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
import re
from collections import defaultdict
from pathlib import Path

GENE_ID_RE = re.compile(r'gene_id "([^"]+)"')

exons = defaultdict(list)
with open("/app/data/genes.gtf") as fh:
    for line in fh:
        if line.startswith("#") or not line.strip():
            continue
        cols = line.rstrip("\n").split("\t")
        if len(cols) < 9 or cols[2] != "exon":
            continue
        m = GENE_ID_RE.search(cols[8])
        if not m:
            continue
        s = int(cols[3])
        e = int(cols[4])
        exons[m.group(1)].append((s, e))

rows = []
for gid, ivs in exons.items():
    ivs = sorted(ivs)
    total = 0
    cur_s, cur_e = None, None
    for s, e in ivs:
        if cur_s is None:
            cur_s, cur_e = s, e
        elif s <= cur_e + 1:
            cur_e = max(cur_e, e)
        else:
            total += cur_e - cur_s + 1
            cur_s, cur_e = s, e
    if cur_s is not None:
        total += cur_e - cur_s + 1
    rows.append((gid, total))

rows.sort()
with open("/app/output/gene_lengths.tsv", "w") as fh:
    fh.write("gene_id\tlength\n")
    for gid, length in rows:
        fh.write(f"{gid}\t{length}\n")
PY
