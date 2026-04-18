#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output

python3 - <<'PY'
import pysam

VCF = "/app/data/variants.vcf.gz"
BED = "/app/data/regions.bed"
OUT = "/app/output/density.tsv"


def classify(ref, alt):
    if alt.startswith("<") or "[" in alt or "]" in alt or alt == "*":
        return None
    bases = set("ACGT")
    if not set(ref.upper()).issubset(bases) or not set(alt.upper()).issubset(bases):
        return None
    if len(ref) == 1 and len(alt) == 1:
        return "snv"
    return "indel"


variants = []  # list of (chrom, pos, kind)
with pysam.VariantFile(VCF) as vcf:
    for rec in vcf:
        for alt in rec.alts or ():
            k = classify(rec.ref, alt)
            if k is None:
                continue
            variants.append((rec.chrom, rec.pos, k))

intervals = []
with open(BED) as fh:
    for line in fh:
        if not line.strip():
            continue
        c, s, e = line.rstrip("\n").split("\t")[:3]
        intervals.append((c, int(s), int(e)))

lines = ["chrom\tstart\tend\tn_snv\tn_indel\tdensity_per_kb"]
for c, s, e in intervals:
    n_snv = sum(1 for (vc, vp, vk) in variants
                if vc == c and s + 1 <= vp <= e and vk == "snv")
    n_indel = sum(1 for (vc, vp, vk) in variants
                  if vc == c and s + 1 <= vp <= e and vk == "indel")
    density = 1000.0 * (n_snv + n_indel) / (e - s)
    lines.append(f"{c}\t{s}\t{e}\t{n_snv}\t{n_indel}\t{density:.4f}")

with open(OUT, "w") as fh:
    fh.write("\n".join(lines) + "\n")
PY
