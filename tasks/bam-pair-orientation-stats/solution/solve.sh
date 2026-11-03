#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
import pysam
from statistics import median

counts = {"FR": [], "RF": [], "TANDEM": []}
bam = pysam.AlignmentFile("/app/data/pairs.bam", "rb")
for a in bam:
    f = a.flag
    if not (f & 0x1) or not (f & 0x2):
        continue
    if not (f & 0x40):
        continue
    if f & (0x100 | 0x800 | 0x400):
        continue
    if (f & 0x4) or (f & 0x8):
        continue
    if a.reference_id != a.next_reference_id:
        continue
    rev, mrev = bool(f & 0x10), bool(f & 0x20)
    if rev == mrev:
        counts["TANDEM"].append(abs(a.template_length))
        continue
    if a.reference_start <= a.next_reference_start:
        left_rev = rev
    else:
        left_rev = mrev
    counts["RF" if left_rev else "FR"].append(abs(a.template_length))

with open("/app/output/pair_orientation.tsv", "w") as fh:
    fh.write("orientation\tn_pairs\tmedian_abs_tlen\n")
    for o in ("FR", "RF", "TANDEM"):
        v = counts[o]
        fh.write(f"{o}\t{len(v)}\t{median(v):.1f}\n" if v else f"{o}\t0\t0.0\n")
PY
