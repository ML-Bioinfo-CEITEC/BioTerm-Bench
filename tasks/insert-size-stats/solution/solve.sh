#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

samtools stats /app/data/reads.bam > /tmp/stats.txt

python3 - <<'PY'
import json

mean = stdev = None
with open("/tmp/stats.txt") as fh:
    for line in fh:
        if not line.startswith("SN\t"):
            continue
        parts = line.rstrip("\n").split("\t")
        key = parts[1].rstrip(":")
        if key == "insert size average":
            mean = float(parts[2])
        elif key == "insert size standard deviation":
            stdev = float(parts[2])

out = {"mean_insert": mean, "stdev_insert": stdev}
with open("/app/output/insert.json", "w") as fh:
    json.dump(out, fh, indent=2, sort_keys=True)
    fh.write("\n")
PY
