#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
import pysam


AUTOSOMES = {str(i) for i in range(1, 23)}


def norm_gt(call):
    gt = call.get("GT")
    if gt is None or len(gt) != 2 or any(a is None for a in gt):
        return None
    return tuple(sorted(int(a) for a in gt))


def dosage(gt):
    if gt is None:
        return None
    return sum(1 for allele in gt if allele != 0)


def is_het(gt):
    return gt is not None and gt[0] != gt[1]


with pysam.VariantFile("/app/data/calls.vcf.gz") as vf:
    samples = list(vf.header.samples)
    sample_rows = {sample: [] for sample in samples}
    sites = []
    for rec in vf:
        if rec.chrom not in AUTOSOMES:
            continue
        if rec.filter.keys() and set(rec.filter.keys()) != {"PASS"}:
            continue
        if len(rec.ref) != 1 or len(rec.alts or []) != 1 or len(rec.alts[0]) != 1:
            continue
        if rec.ref not in "ACGT" or rec.alts[0] not in "ACGT":
            continue
        gt_map = {sample: norm_gt(rec.samples[sample]) for sample in samples}
        for sample in samples:
            sample_rows[sample].append(gt_map[sample])
        sites.append(gt_map)

pair_list = []
with open("/app/data/pairs.tsv") as fh:
    next(fh)
    for line in fh:
        line = line.strip()
        if line:
            a, b = line.split("\t")
            pair_list.append((a, b))

n_sites = len(sites)
with open("/app/output/sample_qc.tsv", "w") as fh:
    fh.write("sample\tn_sites\tn_called\tcall_rate\tn_het\thet_rate\n")
    for sample in samples:
        called = [gt for gt in sample_rows[sample] if gt is not None]
        n_called = len(called)
        n_het = sum(1 for gt in called if is_het(gt))
        fh.write(
            f"{sample}\t{n_sites}\t{n_called}\t{(n_called / n_sites if n_sites else 0.0):.4f}\t"
            f"{n_het}\t{(n_het / n_called if n_called else 0.0):.4f}\n"
        )

with open("/app/output/pair_concordance.tsv", "w") as fh:
    fh.write("sample_a\tsample_b\tn_compared\tconcordance\n")
    for a, b in pair_list:
        compared = 0
        concordant = 0
        for gt_map in sites:
            da = dosage(gt_map[a])
            db = dosage(gt_map[b])
            if da is None or db is None:
                continue
            compared += 1
            if da == db:
                concordant += 1
        fh.write(f"{a}\t{b}\t{compared}\t{(concordant / compared if compared else 0.0):.4f}\n")
PY
