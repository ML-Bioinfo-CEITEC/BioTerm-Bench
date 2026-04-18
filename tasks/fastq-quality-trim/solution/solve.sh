#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
import gzip
import json

Q_THR = 20

n_in = 0
n_out = 0
bases_in = 0
bases_out = 0

with gzip.open("/app/data/reads.fastq.gz", "rt") as fh:
    while True:
        header = fh.readline()
        if not header:
            break
        seq = fh.readline().rstrip("\n")
        plus = fh.readline()
        qual = fh.readline().rstrip("\n")
        n_in += 1
        bases_in += len(seq)

        i = len(qual)
        while i > 0 and (ord(qual[i - 1]) - 33) < Q_THR:
            i -= 1
        if i > 0:
            n_out += 1
            bases_out += i

mean_in = bases_in / n_in if n_in else 0.0
mean_out = bases_out / n_out if n_out else 0.0

out = {
    "n_in": n_in,
    "n_out": n_out,
    "bases_in": bases_in,
    "bases_out": bases_out,
    "mean_len_in": round(mean_in, 4),
    "mean_len_out": round(mean_out, 4),
}
with open("/app/output/stats.json", "w") as fh:
    json.dump(out, fh, indent=2, sort_keys=True)
    fh.write("\n")
PY
