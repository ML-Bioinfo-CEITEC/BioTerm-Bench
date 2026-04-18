#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output

python3 - <<'PY'
import gzip
import numpy as np

OUT = "/app/output/per_base_quality.tsv"
FQ = "/app/data/reads.fastq.gz"

per_pos = {}
with gzip.open(FQ, "rt") as fh:
    while True:
        h = fh.readline()
        if not h:
            break
        _seq = fh.readline().rstrip("\n")
        _plus = fh.readline()
        qline = fh.readline().rstrip("\n")
        for pos, ch in enumerate(qline):
            q = ord(ch) - 33
            per_pos.setdefault(pos, []).append(q)

lines = ["pos\tn\tmean_q\tmedian_q"]
for pos in sorted(per_pos):
    vals = per_pos[pos]
    n = len(vals)
    mean_q = float(np.mean(vals))
    med = float(np.percentile(vals, 50.0))
    lines.append(f"{pos}\t{n}\t{mean_q:.4f}\t{med:.4f}")

with open(OUT, "w") as fh:
    fh.write("\n".join(lines) + "\n")
PY
