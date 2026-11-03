#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
import math

seq = "".join(l.strip() for l in open("/app/data/sequence.fasta") if not l.startswith(">"))

states, init, trans, emit = [], {}, {}, {}
rows = [l.rstrip("\n").split("\t") for l in open("/app/data/model.tsv")]
hdr = rows[0]
for r in rows[1:]:
    s = r[0]
    states.append(s)
    init[s] = float(r[1])
    trans[s] = {"AT_rich": float(r[2]), "GC_rich": float(r[3])}
    emit[s] = {b: float(r[hdr.index("e_" + b)]) for b in "ACGT"}

lg = math.log
delta = {s: lg(init[s]) + lg(emit[s][seq[0]]) for s in states}
back = []
for base in seq[1:]:
    step, nxt = {}, {}
    for s in states:
        best = max(states, key=lambda p: (delta[p] + lg(trans[p][s]), -states.index(p)))
        nxt[s] = delta[best] + lg(trans[best][s]) + lg(emit[s][base])
        step[s] = best
    back.append(step)
    delta = nxt

last = max(states, key=lambda s: (delta[s], -states.index(s)))
path = [last]
for step in reversed(back):
    path.append(step[path[-1]])
path.reverse()

with open("/app/output/segments.tsv", "w") as fh:
    fh.write("start\tend\tstate\tlength\n")
    start = 0
    for i in range(1, len(path) + 1):
        if i == len(path) or path[i] != path[start]:
            fh.write(f"{start + 1}\t{i}\t{path[start]}\t{i - start}\n")
            start = i
PY
