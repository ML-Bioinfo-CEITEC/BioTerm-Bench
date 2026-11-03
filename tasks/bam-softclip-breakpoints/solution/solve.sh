#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
import pysam
from collections import defaultdict

support = defaultdict(list)
bam = pysam.AlignmentFile("/app/data/clips.bam", "rb")
for a in bam:
    if a.flag & (0x100 | 0x800 | 0x400 | 0x4):
        continue
    ct = a.cigartuples or []
    if not ct:
        continue
    chrom = bam.get_reference_name(a.reference_id)
    if ct[0][0] == 4 and ct[0][1] >= 10:
        support[(chrom, "L")].append(a.reference_start)
    if ct[-1][0] == 4 and ct[-1][1] >= 10:
        support[(chrom, "R")].append(a.reference_start + sum(n for op, n in ct if op == 0))

rows = []
for (chrom, side), pts in support.items():
    pts = sorted(pts)
    cur = [pts[0]]
    groups = []
    for p in pts[1:]:
        if p - cur[-1] <= 5:
            cur.append(p)
        else:
            groups.append(cur); cur = [p]
    groups.append(cur)
    for g in groups:
        if len(g) >= 3:
            rows.append((chrom, side, sorted(g)[(len(g) - 1) // 2], len(g)))

rows.sort(key=lambda r: (r[0], r[2], r[1]))
with open("/app/output/breakpoints.tsv", "w") as fh:
    fh.write("chrom\tside\tposition\tn_reads\n")
    for r in rows:
        fh.write("\t".join(map(str, r)) + "\n")
PY
