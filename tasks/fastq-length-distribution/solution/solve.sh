#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
import gzip
from collections import Counter

counts = Counter()
with gzip.open("/app/data/reads.fastq.gz", "rt") as fh:
    while True:
        header = fh.readline()
        if not header:
            break
        seq = fh.readline().rstrip("\n")
        plus = fh.readline()
        qual = fh.readline()
        if not seq or not plus or not qual:
            break
        counts[len(seq)] += 1

with open("/app/output/lengths.tsv", "w") as out:
    out.write("length\tcount\n")
    for L in sorted(counts):
        out.write(f"{L}\t{counts[L]}\n")
PY
