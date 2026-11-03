#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
from collections import defaultdict

K = 21
reads, cur = [], []
for line in open("/app/data/reads.fasta"):
    if line.startswith(">"):
        if cur:
            reads.append("".join(cur)); cur = []
    else:
        cur.append(line.strip())
if cur:
    reads.append("".join(cur))

kmers = set()
for r in reads:
    for i in range(len(r) - K + 1):
        kmers.add(r[i:i + K])

outs, ins = defaultdict(set), defaultdict(set)
for km in kmers:
    outs[km[:-1]].add(km[1:])
    ins[km[1:]].add(km[:-1])

simple = {n for n in set(outs) | set(ins)
          if len(outs.get(n, ())) == 1 and len(ins.get(n, ())) == 1}

seqs, seen = [], set()
for km in sorted(kmers):
    u, v = km[:-1], km[1:]
    if u in simple or (u, v) in seen:
        continue
    seen.add((u, v))
    path = [u, v]
    cur_node = v
    while cur_node in simple:
        nxt = next(iter(outs[cur_node]))
        seen.add((cur_node, nxt))
        path.append(nxt)
        cur_node = nxt
    seqs.append(path[0] + "".join(p[-1] for p in path[1:]))

rows = sorted(seqs, key=lambda s: (-len(s), s))
with open("/app/output/unitigs.tsv", "w") as fh:
    fh.write("unitig_id\tlength\tn_kmers\tsequence\n")
    for i, s in enumerate(rows, start=1):
        fh.write(f"unitig{i:03d}\t{len(s)}\t{len(s) - K + 1}\t{s}\n")
PY
