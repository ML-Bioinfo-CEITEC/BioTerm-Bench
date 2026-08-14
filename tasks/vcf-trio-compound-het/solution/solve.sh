#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
from collections import defaultdict

import pysam


AUTOSOMES = {str(i) for i in range(1, 23)}


def norm_gt(call):
    gt = call.get("GT")
    if gt is None or len(gt) != 2 or any(a is None for a in gt):
        return None
    return tuple(sorted(str(a) for a in gt))


def alt_count(gt):
    if gt is None:
        return None
    return sum(1 for allele in gt if allele != "0")


hits = defaultdict(lambda: {"paternal": [], "maternal": []})
with pysam.VariantFile("/app/data/trio.vcf.gz") as vf:
    for rec in vf:
        if rec.chrom not in AUTOSOMES:
            continue
        if rec.filter.keys() and set(rec.filter.keys()) != {"PASS"}:
            continue
        if len(rec.ref) != 1 or len(rec.alts or []) != 1 or len(rec.alts[0]) != 1:
            continue
        if rec.ref not in "ACGT" or rec.alts[0] not in "ACGT":
            continue
        gene = rec.info.get("GENE")
        if not gene:
            continue
        c = norm_gt(rec.samples["CHILD"])
        f = norm_gt(rec.samples["FATHER"])
        m = norm_gt(rec.samples["MOTHER"])
        if c is None or f is None or m is None:
            continue
        c_alt = alt_count(c)
        f_alt = alt_count(f)
        m_alt = alt_count(m)
        if c_alt == 1 and f_alt >= 1 and m_alt == 0:
            hits[gene]["paternal"].append(rec.pos)
        if c_alt == 1 and m_alt >= 1 and f_alt == 0:
            hits[gene]["maternal"].append(rec.pos)

with open("/app/output/compound_hets.tsv", "w") as fh:
    fh.write("gene\tn_paternal\tn_maternal\tfirst_paternal_pos\tfirst_maternal_pos\n")
    for gene in sorted(hits):
        paternal = sorted(hits[gene]["paternal"])
        maternal = sorted(hits[gene]["maternal"])
        if not paternal or not maternal:
            continue
        fh.write(f"{gene}\t{len(paternal)}\t{len(maternal)}\t{paternal[0]}\t{maternal[0]}\n")
PY
