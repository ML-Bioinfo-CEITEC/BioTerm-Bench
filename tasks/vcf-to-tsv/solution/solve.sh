#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY' > /app/output/variants.tsv
import pysam

vcf = pysam.VariantFile("/app/data/variants.vcf.gz")
print("chrom\tpos\tref\talt\tqual\tdp\tgt\tvtype")
for rec in vcf:
    alt = rec.alts[0] if rec.alts else ""
    qual = "NA" if rec.qual is None else (
        f"{rec.qual:g}" if rec.qual != int(rec.qual) else str(int(rec.qual))
    )
    dp = rec.info.get("DP")
    dp_str = "NA" if dp is None else str(dp)
    sample = next(iter(rec.samples.values()))
    gt = sample.allele_indices
    phased = sample.phased
    sep = "|" if phased else "/"
    gt_str = sep.join("." if g is None else str(g) for g in gt)
    vtype = "snp" if (len(rec.ref) == 1 and len(alt) == 1) else "indel"
    print(f"{rec.chrom}\t{rec.pos}\t{rec.ref}\t{alt}\t{qual}\t{dp_str}\t{gt_str}\t{vtype}")
PY
