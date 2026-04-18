#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

# Use the JSON output mode so we don't have to parse free-form lines.
samtools flagstat -O json /app/data/reads.bam > /tmp/flagstat.json

python3 - <<'PY' > /app/output/metrics.tsv
import json

with open("/tmp/flagstat.json") as fh:
    j = json.load(fh)

qc = j["QC-passed reads"]
rows = {
    "total_reads":     qc["total"],
    "mapped":          qc["mapped"],
    "properly_paired": qc["properly paired"],
    "duplicates":      qc["duplicates"],
    "supplementary":   qc["supplementary"],
}
for k in sorted(rows):
    print(f"{k}\t{rows[k]}")
PY
