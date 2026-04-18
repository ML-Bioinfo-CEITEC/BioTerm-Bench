#!/usr/bin/env python3
"""Generate variants.vcf.gz + gold variants.tsv for vcf-to-tsv.

Hand-crafted, bi-allelic, single-sample VCF with a mix of SNPs and
indels, deliberately varying QUAL (some `.`), DP (a couple missing),
and phased/unphased GTs. Deterministic: no RNG.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

OUT_DATA = Path("/out/data")
OUT_GOLD = Path("/out/gold")

HEADER = [
    "##fileformat=VCFv4.2",
    "##contig=<ID=chr22,length=50818468>",
    "##INFO=<ID=DP,Number=1,Type=Integer,Description=\"Total depth\">",
    "##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">",
    "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tHG001",
]

# (pos, ref, alt, qual_str, dp_or_None, gt, expected_vtype)
RECORDS = [
    ("chr22", 16050001, "A",     "G",      "42",   25,    "0/1",  "snp"),
    ("chr22", 16050150, "T",     "C",      "99",   40,    "1/1",  "snp"),
    ("chr22", 16050400, "CAT",   "C",      "37",   22,    "0/1",  "indel"),
    ("chr22", 16050612, "G",     "GA",     "55.5", 18,    "0|1",  "indel"),
    ("chr22", 16051001, "C",     "T",      "28",   15,    "1/0",  "snp"),
    ("chr22", 16051340, "AAAA",  "A",      ".",    12,    "0/1",  "indel"),
    ("chr22", 16051800, "G",     "A",      "65",   None,  "1/1",  "snp"),
    ("chr22", 16052020, "T",     "G",      "12",   8,     "0/1",  "snp"),
    ("chr22", 16052500, "A",     "ACCC",   "48",   30,    "1|1",  "indel"),
    ("chr22", 16053000, "C",     "G",      ".",    None,  "0/0",  "snp"),
    ("chr22", 16053400, "G",     "T",      "78",   41,    "1/1",  "snp"),
    ("chr22", 16053900, "TA",    "T",      "31",   17,    "0|1",  "indel"),
]


def main() -> None:
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    OUT_GOLD.mkdir(parents=True, exist_ok=True)

    tmp_vcf = OUT_DATA / "_variants.vcf"
    with tmp_vcf.open("w") as fh:
        for line in HEADER:
            fh.write(line + "\n")
        for chrom, pos, ref, alt, qual, dp, gt, _ in RECORDS:
            info = f"DP={dp}" if dp is not None else "."
            fh.write(
                f"{chrom}\t{pos}\t.\t{ref}\t{alt}\t{qual}\tPASS\t{info}"
                f"\tGT\t{gt}\n"
            )

    subprocess.run(
        ["bgzip", "-f", str(tmp_vcf)], check=True
    )
    subprocess.run(
        ["tabix", "-p", "vcf", str(OUT_DATA / "_variants.vcf.gz")], check=True
    )
    (OUT_DATA / "_variants.vcf.gz").rename(OUT_DATA / "variants.vcf.gz")
    (OUT_DATA / "_variants.vcf.gz.tbi").rename(OUT_DATA / "variants.vcf.gz.tbi")

    tsv = ["chrom\tpos\tref\talt\tqual\tdp\tgt\tvtype"]
    for chrom, pos, ref, alt, qual, dp, gt, vtype in RECORDS:
        # Match the pysam/bcftools display convention:
        #   * '.' becomes 'NA'
        #   * integer-valued QUAL has no trailing '.0'
        if qual == ".":
            qual_out = "NA"
        else:
            qf = float(qual)
            qual_out = f"{qf:g}" if qf != int(qf) else str(int(qf))
        dp_out = "NA" if dp is None else str(dp)
        tsv.append(f"{chrom}\t{pos}\t{ref}\t{alt}\t{qual_out}\t{dp_out}\t{gt}\t{vtype}")
    (OUT_GOLD / "variants.tsv").write_text("\n".join(tsv) + "\n")

    print(f"wrote variants.vcf.gz ({len(RECORDS)} records), gold variants.tsv")


if __name__ == "__main__":
    main()
