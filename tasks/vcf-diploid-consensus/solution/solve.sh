#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
import pysam


def load_fasta(path: str):
    seqs = {}
    order = []
    name = None
    chunks = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    seqs[name] = "".join(chunks)
                    order.append(name)
                name = line[1:].split()[0]
                chunks = []
            else:
                chunks.append(line.upper())
        if name is not None:
            seqs[name] = "".join(chunks)
            order.append(name)
    return order, seqs


def wrap(seq: str, width: int = 60) -> str:
    return "\n".join(seq[i:i + width] for i in range(0, len(seq), width))


def build_haps(ref: str, records):
    out = [[], []]
    cursor = 0
    for pos0, ref_allele, alts, gt in records:
        out[0].append(ref[cursor:pos0])
        out[1].append(ref[cursor:pos0])
        left, right = gt
        choices = [ref_allele, *alts]
        out[0].append(choices[left])
        out[1].append(choices[right])
        cursor = pos0 + len(ref_allele)
    out[0].append(ref[cursor:])
    out[1].append(ref[cursor:])
    return "".join(out[0]), "".join(out[1])


order, refs = load_fasta("/app/data/ref.fa")
kept = {chrom: [] for chrom in order}

with pysam.VariantFile("/app/data/variants.vcf.gz") as vcf:
    for rec in vcf:
        filt = list(rec.filter.keys())
        if filt and filt != ["PASS"]:
            continue
        gt = rec.samples["SAMPLE"].get("GT")
        phased = rec.samples["SAMPLE"].phased
        if not phased or gt is None or len(gt) != 2 or any(x is None for x in gt):
            continue
        alleles = [rec.ref, *(rec.alts or [])]
        if any(set(allele.upper()) - set("ACGT") for allele in alleles):
            continue
        kept[rec.chrom].append((rec.pos - 1, rec.ref, list(rec.alts or ()), tuple(int(x) for x in gt)))

with open("/app/output/consensus.fa", "w") as fh:
    for chrom in order:
        hap1, hap2 = build_haps(refs[chrom], kept[chrom])
        fh.write(f">{chrom}|hap1\n{wrap(hap1)}\n")
        fh.write(f">{chrom}|hap2\n{wrap(hap2)}\n")
PY
