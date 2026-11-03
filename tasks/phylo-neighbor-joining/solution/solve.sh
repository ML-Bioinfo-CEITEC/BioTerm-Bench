#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
rows = [ln.rstrip("\n").split("\t") for ln in open("/app/data/distances.tsv")]
names = rows[0][1:]
dm = {}
for r in rows[1:]:
    for j, name in enumerate(names):
        dm[(r[0], name)] = float(r[j + 1])

steps, counter = [], 0
while len(names) > 2:
    n = len(names)
    total = {x: sum(dm[(x, y)] for y in names if y != x) for x in names}
    best = None
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            q = (n - 2) * dm[(a, b)] - total[a] - total[b]
            key = (round(q, 9),) + tuple(sorted((a, b)))
            if best is None or key < best[0]:
                best = (key, a, b)
    _, a, b = best
    la = dm[(a, b)] / 2 + (total[a] - total[b]) / (2 * (n - 2))
    lb = dm[(a, b)] - la
    counter += 1
    u = f"N{counter}"
    lens = {a: la, b: lb}
    first, second = sorted((a, b))
    steps.append((counter, first, second, lens[first], lens[second]))
    for k in list(names):
        if k in (a, b):
            continue
        dm[(u, k)] = dm[(k, u)] = (dm[(a, k)] + dm[(b, k)] - dm[(a, b)]) / 2
    dm[(u, u)] = 0.0
    names = [x for x in names if x not in (a, b)] + [u]

a, b = sorted(names)
steps.append((counter + 1, a, b, dm[(a, b)], 0.0))

with open("/app/output/nj_steps.tsv", "w") as fh:
    fh.write("step\tnode_a\tnode_b\tlen_a\tlen_b\n")
    for s, x, y, lx, ly in steps:
        fh.write(f"{s}\t{x}\t{y}\t{lx:.4f}\t{ly:.4f}\n")
PY
