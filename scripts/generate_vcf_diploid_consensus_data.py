#!/usr/bin/env python3
"""Generate reference + phased multiallelic VCF for diploid consensus.

Writes:
  $OUT_DIR/data/ref.fa
  $OUT_DIR/data/variants.vcf.gz
  $OUT_DIR/data/variants.vcf.gz.tbi
  $OUT_DIR/gold/consensus.fa
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

OUT_ROOT = Path(os.environ.get("OUT_DIR", "/out"))
DATA_DIR = OUT_ROOT / "data"
GOLD_DIR = OUT_ROOT / "gold"
REF_PATH = DATA_DIR / "ref.fa"
VCF_PATH = DATA_DIR / "variants.vcf.gz"
GOLD_PATH = GOLD_DIR / "consensus.fa"

CONTIGS = {
    "chrVC1": list("ACGTGCTAGCTTACGATCGATCGGCTAACGTTACCGGATCGAATTCGACCTAGGCTAACGTAGCTTA"),
    "chrVC2": list("TTGACCGTACGATCGTAGCTAGGCTAACCGTTAGGCTAACCGATGCTTAGCATCGATCG"),
}

VARIANTS = [
    ("chrVC1", 5, "G", ["T"], "PASS", "1|0"),
    ("chrVC1", 12, "T", ["TAA"], ".", "0|1"),
    ("chrVC1", 20, "ATC", ["A", "ATGGC"], "PASS", "2|1"),
    ("chrVC1", 35, "CG", ["C"], "PASS", "1|0"),
    ("chrVC1", 50, "C", ["T"], "LowQual", "1|1"),
    ("chrVC1", 60, "G", ["A"], "PASS", "0/1"),
    ("chrVC2", 10, "C", ["A", "T"], "PASS", "2|2"),
    ("chrVC2", 25, "T", ["G"], "PASS", ".|1"),
    ("chrVC2", 40, "C", ["<DEL>"], "PASS", "1|0"),
    ("chrVC2", 55, "GA", ["G"], "PASS", "0|1"),
]


def wrap_fasta(seq: str, width: int = 60) -> str:
    return "\n".join(seq[i:i + width] for i in range(0, len(seq), width))


def apply_consensus(ref: str, records: list[tuple[int, str, list[str], str]]) -> tuple[str, str]:
    out = [[], []]
    cursor = 1
    for pos, ref_allele, alts, gt in records:
        left_idx, right_idx = [int(x) for x in gt.split("|")]
        out[0].append(ref[cursor - 1:pos - 1])
        out[1].append(ref[cursor - 1:pos - 1])
        choices = [ref_allele, *alts]
        out[0].append(choices[left_idx])
        out[1].append(choices[right_idx])
        cursor = pos + len(ref_allele)
    out[0].append(ref[cursor - 1:])
    out[1].append(ref[cursor - 1:])
    return ("".join(out[0]), "".join(out[1]))


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    with REF_PATH.open("w") as fh:
        for chrom, seq_list in CONTIGS.items():
            seq = "".join(seq_list)
            fh.write(f">{chrom}\n{wrap_fasta(seq)}\n")

    header = [
        "##fileformat=VCFv4.2",
        "##FILTER=<ID=PASS,Description=\"All filters passed\">",
        "##FILTER=<ID=LowQual,Description=\"Low quality\">",
        "##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">",
    ]
    for chrom, seq_list in CONTIGS.items():
        header.append(f"##contig=<ID={chrom},length={len(seq_list)}>")
    header.append("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE")

    plain_vcf = OUT_ROOT / "variants.vcf"
    with plain_vcf.open("w") as fh:
        fh.write("\n".join(header) + "\n")
        for chrom, pos, ref_allele, alts, filt, gt in VARIANTS:
            ref_seq = "".join(CONTIGS[chrom][pos - 1:pos - 1 + len(ref_allele)])
            if ref_seq != ref_allele:
                raise ValueError(f"reference mismatch at {chrom}:{pos} expected {ref_allele} got {ref_seq}")
            fh.write(
                f"{chrom}\t{pos}\t.\t{ref_allele}\t{','.join(alts)}\t60.0\t{filt}\t.\tGT\t{gt}\n"
            )

    subprocess.check_call(["bgzip", "-f", str(plain_vcf)])
    subprocess.check_call(["tabix", "-f", "-p", "vcf", f"{plain_vcf}.gz"])
    shutil.move(f"{plain_vcf}.gz", VCF_PATH)
    shutil.move(f"{plain_vcf}.gz.tbi", f"{VCF_PATH}.tbi")

    with GOLD_PATH.open("w") as fh:
        for chrom, seq_list in CONTIGS.items():
            ref = "".join(seq_list)
            kept = []
            for c, pos, ref_allele, alts, filt, gt in VARIANTS:
                if c != chrom:
                    continue
                if filt not in {"PASS", "."}:
                    continue
                if "|" not in gt or "/" in gt or "." in gt:
                    continue
                if any(set(allele) - set("ACGT") for allele in [ref_allele, *alts]):
                    continue
                kept.append((pos, ref_allele, alts, gt))
            hap1, hap2 = apply_consensus(ref, kept)
            fh.write(f">{chrom}|hap1\n{wrap_fasta(hap1)}\n")
            fh.write(f">{chrom}|hap2\n{wrap_fasta(hap2)}\n")
    print(f"wrote {REF_PATH}, {VCF_PATH}, {VCF_PATH}.tbi, {GOLD_PATH}")


if __name__ == "__main__":
    main()
