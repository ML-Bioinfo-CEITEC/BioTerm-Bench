#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

samtools depth -a /app/data/reads.bam > /tmp/depth.tsv

python3 - <<'PY' > /app/output/coverage.json
import json
from statistics import median

depths = []
with open("/tmp/depth.tsv") as fh:
    for line in fh:
        cols = line.rstrip("\n").split("\t")
        depths.append(int(cols[2]))

n = len(depths)
covered = sum(1 for d in depths if d >= 1)
out = {
    "ref_length":       n,
    "mean_depth":       sum(depths) / n if n else 0.0,
    "median_depth":     int(sorted(depths)[(n - 1) // 2]) if n else 0,
    "fraction_covered": covered / n if n else 0.0,
    "max_depth":        max(depths) if depths else 0,
}
print(json.dumps(out, indent=2, sort_keys=True))
PY
