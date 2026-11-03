#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
import gzip
from collections import defaultdict

order = {"chr1": 0, "chr2": 1}
blocks = defaultdict(list)
with gzip.open("/app/data/phased.vcf.gz", "rt") as fh:
    for line in fh:
        if line.startswith("#"):
            continue
        f = line.rstrip("\n").split("\t")
        keys, vals = f[8].split(":"), f[9].split(":")
        s = dict(zip(keys, vals))
        gt = s.get("GT", "")
        if "|" not in gt or "PS" not in s:
            continue
        a, b = gt.split("|")
        if a == b:
            continue
        blocks[(f[0], int(s["PS"]))].append(int(f[1]))

rows = []
for (chrom, ps), pos in blocks.items():
    if len(pos) < 2:
        continue
    pos.sort()
    gaps = [y - x for x, y in zip(pos, pos[1:])]
    rows.append((chrom, ps, len(pos), pos[0], pos[-1], pos[-1] - pos[0] + 1, max(gaps)))

rows.sort(key=lambda r: (order[r[0]], r[1]))
with open("/app/output/phase_blocks.tsv", "w") as fh:
    fh.write("chrom\tphase_set\tn_variants\tstart\tend\tspan\tmax_gap\n")
    for r in rows:
        fh.write("\t".join(map(str, r)) + "\n")
PY
