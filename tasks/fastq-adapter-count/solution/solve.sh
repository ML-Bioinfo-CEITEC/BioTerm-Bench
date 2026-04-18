#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
import gzip, json

adapter = open("/app/data/adapter.txt").read().strip()

total = 0
hits = 0
with gzip.open("/app/data/reads.fastq.gz", "rt") as fh:
    while True:
        h = fh.readline()
        if not h:
            break
        seq = fh.readline().rstrip("\n")
        fh.readline()
        fh.readline()
        total += 1
        if adapter in seq:
            hits += 1

out = {"total_reads": total, "adapter_reads": hits, "adapter_seq": adapter}
with open("/app/output/counts.json", "w") as fh:
    json.dump(out, fh, indent=2, sort_keys=True)
    fh.write("\n")
PY
