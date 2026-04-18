#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY' > /app/output/summary.json
import json
import pysam

TRANSITIONS = {("A", "G"), ("G", "A"), ("C", "T"), ("T", "C")}

vcf = pysam.VariantFile("/app/data/region.vcf.gz")
n_records = n_snps = n_indels = 0
ti = tv = 0
het = hom = 0

for rec in vcf:
    for alt in rec.alts or ():
        n_records += 1
        ref = rec.ref
        if len(ref) == 1 and len(alt) == 1:
            n_snps += 1
            pair = (ref.upper(), alt.upper())
            if pair in TRANSITIONS:
                ti += 1
            else:
                tv += 1
        if len(ref) != len(alt):
            n_indels += 1
    # genotype of the first sample only
    sample = next(iter(rec.samples.values()))
    gt = sample["GT"]
    if gt and all(g is not None for g in gt):
        if len(set(gt)) == 1 and gt[0] != 0:
            hom += 1
        elif any(g == 0 for g in gt) != all(g == 0 for g in gt):
            het += 1

out = {
    "n_records": n_records,
    "n_snps":    n_snps,
    "n_indels":  n_indels,
    "ti_tv":     ti / tv if tv else 0.0,
    "het_hom":   het / hom if hom else 0.0,
}
print(json.dumps(out, sort_keys=True, indent=2))
PY
