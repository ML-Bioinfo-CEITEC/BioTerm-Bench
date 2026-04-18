#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY' > /app/output/stats.tsv
from pathlib import Path

fa = Path("/app/data/sequences.fa").read_text().splitlines()

records = []
cur_id = None
cur_chunks: list[str] = []
for line in fa:
    if line.startswith(">"):
        if cur_id is not None:
            records.append((cur_id, "".join(cur_chunks)))
        cur_id = line[1:].split()[0]
        cur_chunks = []
    else:
        cur_chunks.append(line.strip())
if cur_id is not None:
    records.append((cur_id, "".join(cur_chunks)))

print("seq_id\tlength\tgc_percent\tn_percent")
for sid, seq in records:
    length = len(seq)
    if length == 0:
        gc_pct = 0.0
        n_pct = 0.0
    else:
        u = seq.upper()
        gc_pct = 100.0 * (u.count("G") + u.count("C")) / length
        n_pct = 100.0 * u.count("N") / length
    print(f"{sid}\t{length}\t{gc_pct:.2f}\t{n_pct:.2f}")
PY
