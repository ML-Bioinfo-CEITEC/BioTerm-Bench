#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
import re
from collections import defaultdict

exons = defaultdict(list)
cds = defaultdict(list)
meta = {}
for line in open("/app/data/annotation.gtf"):
    if line.startswith("#"):
        continue
    f = line.rstrip("\n").split("\t")
    if len(f) < 9:
        continue
    feat, s, e, strand, attrs = f[2], int(f[3]), int(f[4]), f[6], f[8]
    tx = re.search(r'transcript_id "([^"]+)"', attrs)
    gene = re.search(r'gene_id "([^"]+)"', attrs)
    if not tx:
        continue
    tx = tx.group(1)
    if feat == "exon":
        exons[tx].append((s, e))
        meta[tx] = (gene.group(1) if gene else "", strand)
    elif feat == "CDS":
        cds[tx].append((s, e))
        meta[tx] = (gene.group(1) if gene else "", strand)

rows = []
for tx, parts in cds.items():
    cs, ce = min(p[0] for p in parts), max(p[1] for p in parts)
    ex = exons.get(tx, [])
    up = sum(max(0, min(e, cs - 1) - s + 1) for s, e in ex)
    down = sum(max(0, e - max(s, ce + 1) + 1) for s, e in ex)
    cds_len = sum(e - s + 1 for s, e in parts)
    gene, strand = meta[tx]
    utr5, utr3 = (up, down) if strand == "+" else (down, up)
    rows.append((tx, gene, strand, utr5, utr3, cds_len))

rows.sort(key=lambda r: r[0])
with open("/app/output/utr_lengths.tsv", "w") as fh:
    fh.write("tx_id\tgene_id\tstrand\tutr5_len\tutr3_len\tcds_len\n")
    for r in rows:
        fh.write("\t".join(map(str, r)) + "\n")
PY
