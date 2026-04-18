#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
import json
import re
import numpy as np
import pysam

CIGAR_RE = re.compile(r"(\d+)([MIDNSHP=X])")

totals = []
n_mapped = 0
with pysam.AlignmentFile("/app/data/reads.bam", "rb") as bam:
    for rec in bam.fetch(until_eof=True):
        if rec.is_unmapped or rec.is_secondary or rec.is_supplementary:
            continue
        n_mapped += 1
        cig = rec.cigarstring or ""
        ops = CIGAR_RE.findall(cig)
        lc = int(ops[0][0]) if ops and ops[0][1] == "S" else 0
        rc = int(ops[-1][0]) if ops and ops[-1][1] == "S" else 0
        totals.append(lc + rc)

n_with = sum(1 for t in totals if t > 0)
mean_t = float(np.mean(totals)) if totals else 0.0
clipped = [t for t in totals if t > 0]
p90 = float(np.percentile(clipped, 90)) if clipped else 0.0

out = {
    "n_primary_mapped": n_mapped,
    "n_with_any_clip": n_with,
    "mean_total_clip": round(mean_t, 4),
    "p90_total_clip": round(p90, 4),
}
with open("/app/output/stats.json", "w") as fh:
    json.dump(out, fh, indent=2, sort_keys=True)
    fh.write("\n")
PY
