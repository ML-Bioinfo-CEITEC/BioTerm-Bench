#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
from collections import defaultdict

HAPS = ["0-0", "0-1", "1-0", "1-1"]
per = defaultdict(list)
with open("/app/data/genotypes.tsv") as fh:
    next(fh)
    for line in fh:
        pid, _s, g1, g2 = line.rstrip("\n").split("\t")
        per[pid].append((int(g1), int(g2)))

with open("/app/output/haplotype_freqs.tsv", "w") as fh:
    fh.write("pair_id\thaplotype\tfrequency\n")
    for pid in sorted(per):
        f = {h: 0.25 for h in HAPS}
        for _ in range(200):
            counts = {h: 0.0 for h in HAPS}
            for g1, g2 in per[pid]:
                if g1 == 1 and g2 == 1:
                    p1 = 2 * f["0-0"] * f["1-1"]
                    p2 = 2 * f["0-1"] * f["1-0"]
                    tot = p1 + p2
                    w1 = 0.5 if tot == 0 else p1 / tot
                    counts["0-0"] += w1
                    counts["1-1"] += w1
                    counts["0-1"] += 1 - w1
                    counts["1-0"] += 1 - w1
                    continue
                a1 = [0, 0] if g1 == 0 else ([0, 1] if g1 == 1 else [1, 1])
                a2 = [0, 0] if g2 == 0 else ([0, 1] if g2 == 1 else [1, 1])
                counts[f"{a1[0]}-{a2[0]}"] += 1
                counts[f"{a1[1]}-{a2[1]}"] += 1
            n = sum(counts.values())
            f = {h: counts[h] / n for h in HAPS}
        for h in HAPS:
            fh.write(f"{pid}\t{h}\t{f[h]:.6f}\n")
PY
