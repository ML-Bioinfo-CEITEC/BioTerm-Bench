#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

samtools markdup /app/data/reads.bam /tmp/marked.bam
samtools flagstat -O json /tmp/marked.bam > /tmp/flagstat.json

python3 - <<'PY'
import json

with open("/tmp/flagstat.json") as fh:
    j = json.load(fh)

qc = j["QC-passed reads"]
out = {"duplicates": qc["duplicates"], "primary_total": qc["primary"]}
with open("/app/output/counts.json", "w") as fh:
    json.dump(out, fh, indent=2, sort_keys=True)
    fh.write("\n")
PY
