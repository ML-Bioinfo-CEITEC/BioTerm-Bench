#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
import json
import pysam

AUTO_SEX = {"X", "Y", "MT", "chrX", "chrY", "chrM", "chrMT"}


def is_consistent(child_alleles, father_alleles, mother_alleles):
    ca = set(child_alleles)
    for a in father_alleles:
        for b in mother_alleles:
            if {a, b} == ca:
                return True
    return False


n_sites = 0
n_viol = 0

with pysam.VariantFile("/app/data/trio.vcf.gz") as vcf:
    samples = list(vcf.header.samples)
    assert samples == ["CHILD", "FATHER", "MOTHER"], samples
    for rec in vcf:
        chrom = rec.chrom
        if chrom in AUTO_SEX:
            continue
        filt = list(rec.filter.keys())
        if filt and filt != ["PASS"]:
            continue
        if not rec.ref or len(rec.ref) != 1 or rec.ref.upper() not in "ACGT":
            continue
        if not rec.alts or len(rec.alts) != 1:
            continue
        alt = rec.alts[0]
        if len(alt) != 1 or alt.upper() not in "ACGT":
            continue

        gts = {}
        bad = False
        for s in samples:
            g = rec.samples[s]["GT"]
            if g is None or any(a is None for a in g):
                bad = True
                break
            gts[s] = tuple(int(a) for a in g)
        if bad:
            continue

        n_sites += 1
        if not is_consistent(gts["CHILD"], gts["FATHER"], gts["MOTHER"]):
            n_viol += 1

rate = round(n_viol / n_sites, 4) if n_sites else 0.0
out = {
    "n_sites": n_sites,
    "n_violations": n_viol,
    "violation_rate": rate,
}
with open("/app/output/summary.json", "w") as fh:
    json.dump(out, fh, indent=2, sort_keys=True)
    fh.write("\n")
PY
