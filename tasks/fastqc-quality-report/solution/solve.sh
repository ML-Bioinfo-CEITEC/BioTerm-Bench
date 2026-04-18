#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output /tmp/fastqc

fastqc -q -o /tmp/fastqc /app/data/reads.fastq.gz

REPORT_DIR=$(find /tmp/fastqc -maxdepth 1 -type d -name '*_fastqc' | head -1)
# FastQC 0.12 uses a zip + extracted directory; unzip if needed.
if [[ -z "${REPORT_DIR}" ]]; then
    ZIP=$(ls /tmp/fastqc/*_fastqc.zip | head -1)
    unzip -q -d /tmp/fastqc "${ZIP}"
    REPORT_DIR=$(find /tmp/fastqc -maxdepth 1 -type d -name '*_fastqc' | head -1)
fi
DATA_TXT="${REPORT_DIR}/fastqc_data.txt"

python3 - "${DATA_TXT}" <<'PY' > /app/output/qc_summary.json
import json
import sys

path = sys.argv[1]
with open(path) as fh:
    lines = fh.read().splitlines()

def basic(key):
    for line in lines:
        if line.startswith(key + "\t"):
            return line.split("\t", 1)[1].strip()
    raise SystemExit(f"missing basic stat: {key}")

total = int(basic("Total Sequences"))
sl = basic("Sequence length")
if "-" in sl:
    lo, hi = sl.split("-")
    smin, smax = int(lo), int(hi)
else:
    smin = smax = int(sl)
gc = int(basic("%GC"))

# Per-base quality module: count positions with mean >= 20.
in_block = False
n_bases = n_good = 0
for line in lines:
    if line.startswith(">>Per base sequence quality"):
        in_block = True
        continue
    if in_block:
        if line.startswith(">>END_MODULE"):
            break
        if line.startswith("#") or not line.strip():
            continue
        cols = line.split("\t")
        mean = float(cols[1])
        n_bases += 1
        if mean >= 20.0:
            n_good += 1

q20_frac = n_good / n_bases if n_bases else 0.0

print(json.dumps({
    "total_sequences":     total,
    "sequence_length_min": smin,
    "sequence_length_max": smax,
    "gc_content":          gc,
    "per_base_q20_frac":   q20_frac,
}, sort_keys=True, indent=2))
PY
