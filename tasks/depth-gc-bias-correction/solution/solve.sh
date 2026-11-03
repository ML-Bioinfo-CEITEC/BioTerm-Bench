#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
import statistics
from collections import defaultdict

rows = []
with open("/app/data/windows.tsv") as fh:
    next(fh)
    for line in fh:
        c, s, e, gc, dp = line.rstrip("\n").split("\t")
        rows.append((c, int(s), int(e), float(gc), float(dp)))


def gc_bin(gc):
    return min(19, int(gc * 20))


by_bin = defaultdict(list)
for r in rows:
    by_bin[gc_bin(r[3])].append(r[4])

overall = statistics.median([r[4] for r in rows])
factors = {}
for b, vals in by_bin.items():
    med = statistics.median(vals)
    factors[b] = 1.0 if len(vals) < 50 or med == 0 else overall / med

corrected = [(r[0], r[1], r[2], r[3], r[4], r[4] * factors[gc_bin(r[3])]) for r in rows]
cmed = statistics.median([x[5] for x in corrected])
lo, hi = 0.5 * cmed, 1.5 * cmed

order = {"chr1": 0, "chr2": 1, "chr3": 2}
flagged = sorted((x for x in corrected if x[5] < lo or x[5] > hi),
                 key=lambda x: (order[x[0]], x[1]))

with open("/app/output/flagged_windows.tsv", "w") as fh:
    fh.write("chrom\tstart\tend\tgc\traw_depth\tcorrected_depth\tflag\n")
    for c, s, e, gc, dp, cd in flagged:
        fh.write(f"{c}\t{s}\t{e}\t{gc:.4f}\t{dp:.2f}\t{cd:.4f}\t"
                 f"{'low' if cd < lo else 'high'}\n")
PY
