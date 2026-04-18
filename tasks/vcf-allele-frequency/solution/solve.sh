#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
import pysam

rows = []
with pysam.VariantFile("/app/data/calls.vcf.gz") as vf:
    sample = list(vf.header.samples)[0]
    for rec in vf:
        ad = rec.samples[sample].get("AD")
        if ad is None or len(ad) < 2:
            continue
        ra, aa = int(ad[0]), int(ad[1])
        total = ra + aa
        if total == 0:
            continue
        af = aa / total
        rows.append((rec.chrom, rec.pos, af))

with open("/app/output/af.tsv", "w") as fh:
    fh.write("CHROM\tPOS\tAF\n")
    for chrom, pos, af in rows:
        fh.write(f"{chrom}\t{pos}\t{af:.6f}\n")
PY
