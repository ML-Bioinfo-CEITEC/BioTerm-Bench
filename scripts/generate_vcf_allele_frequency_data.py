#!/usr/bin/env python3
"""Generate a single-sample VCF with AD fields + gold AF table.

Hand-crafted bi-allelic variants with deterministic AD values. Each
record's allele frequency is defined as ALT_AD / (REF_AD + ALT_AD).
Records with total AD == 0 are intentionally included to test that
they are skipped in the output.

Writes:
  /out/data/calls.vcf.gz
  /out/data/calls.vcf.gz.tbi
  /out/gold/af.tsv       columns: CHROM POS AF  (AF is skipped-row-aware)
"""
from __future__ import annotations

import subprocess
from pathlib import Path

DATA = Path("/out/data")
GOLD = Path("/out/gold/af.tsv")

HEADER = [
    "##fileformat=VCFv4.2",
    "##contig=<ID=chr22,length=50818468>",
    "##INFO=<ID=DP,Number=1,Type=Integer,Description=\"Total depth\">",
    "##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">",
    "##FORMAT=<ID=AD,Number=R,Type=Integer,Description=\"Allelic depths\">",
    "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE",
]

# (pos, ref, alt, ref_ad, alt_ad) — a row with ref_ad=alt_ad=0 must be
# skipped; all other rows must appear.
RECORDS = [
    ("chr22", 16050001, "A", "G",   10, 30),
    ("chr22", 16050150, "T", "C",    0, 40),
    ("chr22", 16050400, "C", "T",   25, 25),
    ("chr22", 16050612, "G", "A",    5, 15),
    ("chr22", 16051001, "C", "T",   50,  0),
    ("chr22", 16051340, "A", "G",    0,  0),   # <- skipped row
    ("chr22", 16051800, "G", "A",    7, 28),
    ("chr22", 16052020, "T", "G",   11,  2),
    ("chr22", 16052500, "A", "C",    1, 19),
    ("chr22", 16053000, "C", "G",    3,  6),
]


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    tmp = DATA / "_calls.vcf"
    with tmp.open("w") as fh:
        for line in HEADER:
            fh.write(line + "\n")
        for chrom, pos, ref, alt, ra, aa in RECORDS:
            dp = ra + aa
            info = f"DP={dp}" if dp > 0 else "DP=0"
            fh.write(
                f"{chrom}\t{pos}\t.\t{ref}\t{alt}\t99\tPASS\t{info}"
                f"\tGT:AD\t0/1:{ra},{aa}\n"
            )

    subprocess.check_call(["bgzip", "-f", str(tmp)])
    subprocess.check_call(
        ["tabix", "-p", "vcf", str(DATA / "_calls.vcf.gz")]
    )
    (DATA / "_calls.vcf.gz").rename(DATA / "calls.vcf.gz")
    (DATA / "_calls.vcf.gz.tbi").rename(DATA / "calls.vcf.gz.tbi")

    with GOLD.open("w") as fh:
        fh.write("CHROM\tPOS\tAF\n")
        for chrom, pos, ref, alt, ra, aa in RECORDS:
            total = ra + aa
            if total == 0:
                continue
            af = aa / total
            fh.write(f"{chrom}\t{pos}\t{af:.6f}\n")

    print(f"wrote calls.vcf.gz ({len(RECORDS)} records) and gold af.tsv")


if __name__ == "__main__":
    main()
