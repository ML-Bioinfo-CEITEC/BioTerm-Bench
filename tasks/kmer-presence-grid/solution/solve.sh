#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY' > /app/output/presence.tsv
from pathlib import Path

kmers = [k.strip() for k in Path("/app/data/kmers.txt").read_text().splitlines() if k.strip()]
kmers.sort()

genomes_dir = Path("/app/data/genomes")
genome_files = sorted(genomes_dir.glob("*.fa"))

rows = []
for gf in genome_files:
    gid = gf.stem
    lines = gf.read_text().splitlines()
    seq = "".join(l.upper() for l in lines if not l.startswith(">"))
    for k in kmers:
        present = 1 if k in seq else 0
        rows.append((gid, k, present))

# Already ordered by file-sort + kmer-sort, but be explicit
rows.sort(key=lambda r: (r[0], r[1]))
for gid, k, p in rows:
    print(f"{gid}\t{k}\t{p}")
PY
