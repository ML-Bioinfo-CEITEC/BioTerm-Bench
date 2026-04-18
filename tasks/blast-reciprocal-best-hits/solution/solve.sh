#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output /tmp/rbh
cd /tmp/rbh

makeblastdb -in /app/data/proteome_a.fa -dbtype prot -out db_a >/dev/null
makeblastdb -in /app/data/proteome_b.fa -dbtype prot -out db_b >/dev/null

blastp -query /app/data/proteome_a.fa -db db_b \
    -outfmt 6 -num_threads 1 -evalue 1e-5 > a_vs_b.tsv
blastp -query /app/data/proteome_b.fa -db db_a \
    -outfmt 6 -num_threads 1 -evalue 1e-5 > b_vs_a.tsv

python3 - <<'PY'
def best_per_query(path):
    best = {}
    with open(path) as fh:
        for line in fh:
            f = line.rstrip("\n").split("\t")
            q, s = f[0], f[1]
            ev = float(f[10]); bs = float(f[11])
            cur = best.get(q)
            cand = (-bs, ev, s, s)
            if cur is None or cand < cur:
                best[q] = cand
    return {q: v[2] for q, v in best.items()}

a2b = best_per_query("/tmp/rbh/a_vs_b.tsv")
b2a = best_per_query("/tmp/rbh/b_vs_a.tsv")

rbh = []
for a, b in a2b.items():
    if b2a.get(b) == a:
        rbh.append((a, b))
rbh.sort()

with open("/app/output/rbh.tsv", "w") as fh:
    for a, b in rbh:
        fh.write(f"{a}\t{b}\n")
PY
