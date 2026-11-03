#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
from scipy.stats import fisher_exact

rows = []
with open("/app/data/counts.tsv") as fh:
    next(fh)
    for line in fh:
        g, a, b, c, e = line.rstrip("\n").split("\t")
        rows.append((g, int(a), int(b), int(c), int(e)))

p = [fisher_exact([[r[1], r[2]], [r[3], r[4]]])[1] for r in rows]
n = len(p)
order = sorted(range(n), key=lambda k: (p[k], rows[k][0]))
q = [0.0] * n
running = 1.0
for rank in range(n, 0, -1):
    k = order[rank - 1]
    running = min(running, p[k] * n / rank)
    q[k] = running

with open("/app/output/significant.tsv", "w") as fh:
    fh.write("gene\talt_case\tref_case\talt_control\tref_control\tp_value\tq_value\n")
    for k in order:
        if q[k] >= 0.05:
            continue
        g, a, b, c, e = rows[k]
        fh.write(f"{g}\t{a}\t{b}\t{c}\t{e}\t{p[k]:.6e}\t{q[k]:.6e}\n")
PY
