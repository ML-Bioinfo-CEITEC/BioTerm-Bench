#!/usr/bin/env python3
"""Slice the GIAB truth VCF to a chr22 region and compute gold summary stats.

Writes:
  /out/data/region.vcf.gz   (+ .tbi)
  /out/gold/summary.json
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pysam

SRC = "/opt/references/giab/HG002_GRCh38_chr22_truth.vcf.gz"
REGION = "chr22:30000000-35000000"

DATA = Path("/out/data/region.vcf.gz")
GOLD = Path("/out/gold/summary.json")

TRANSITIONS = {("A", "G"), ("G", "A"), ("C", "T"), ("T", "C")}


def main() -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    # Slice with bcftools + bgzip + tabix for correctness.
    subprocess.check_call(
        ["bcftools", "view", "-r", REGION, "-Oz", "-o", str(DATA), SRC]
    )
    subprocess.check_call(["tabix", "-f", "-p", "vcf", str(DATA)])

    vcf = pysam.VariantFile(str(DATA))
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
    GOLD.write_text(json.dumps(out, sort_keys=True, indent=2) + "\n")
    print("gold:", json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main()
