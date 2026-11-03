#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
from collections import defaultdict

by_chrom = defaultdict(list)
with open("/app/data/orthologs.tsv") as fh:
    next(fh)
    for line in fh:
        _ga, ca, ia, _gb, cb, ib = line.rstrip("\n").split("\t")
        by_chrom[ca].append((int(ia), cb, int(ib)))

blocks = []
for ca in sorted(by_chrom):
    items = sorted(by_chrom[ca])
    cur = [items[0]]
    for prev, nxt in zip(items, items[1:]):
        step = nxt[2] - prev[2]
        cont = nxt[1] == prev[1] and 1 <= abs(step) <= 3 and (
            len(cur) == 1 or (step > 0) == (cur[-1][2] - cur[-2][2] > 0))
        if cont:
            cur.append(nxt)
        else:
            if len(cur) >= 3:
                blocks.append((ca, cur))
            cur = [nxt]
    if len(cur) >= 3:
        blocks.append((ca, cur))

rows = []
for ca, chain in blocks:
    orient = "+" if chain[-1][2] > chain[0][2] else "-"
    rows.append((ca, chain[0][1], orient, len(chain), chain[0][0], chain[-1][0]))
rows.sort(key=lambda r: (r[0], r[4]))

with open("/app/output/synteny_blocks.tsv", "w") as fh:
    fh.write("chrom_a\tchrom_b\torientation\tn_pairs\tstart_a\tend_a\n")
    for r in rows:
        fh.write("\t".join(map(str, r)) + "\n")
PY
