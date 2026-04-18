#!/usr/bin/env python3
"""Generate a synthetic VCF with mixed QUAL/DP and gold-filtered VCF.

Writes:
  /out/data/calls.vcf.gz (+ .tbi)
  /out/gold/passed.vcf.gz (+ .tbi)
"""
from __future__ import annotations

import random
import subprocess
from pathlib import Path

SEED = 20250418
N_RECORDS = 500

HEADER = """##fileformat=VCFv4.2
##FILTER=<ID=PASS,Description="All filters passed">
##contig=<ID=22,length=50818468>
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total depth">
##INFO=<ID=AF,Number=1,Type=Float,Description="Allele frequency">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO
"""

BASES = "ACGT"
TMP_VCF = Path("/tmp/calls.vcf")
DATA = Path("/out/data/calls.vcf.gz")
GOLD = Path("/out/gold/passed.vcf.gz")


def main() -> None:
    rng = random.Random(SEED)
    DATA.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    with TMP_VCF.open("w") as fh:
        fh.write(HEADER)
        used_positions: set[int] = set()
        for i in range(N_RECORDS):
            while True:
                pos = rng.randint(16_000_001, 16_000_000 + 10_000_000)
                if pos not in used_positions:
                    used_positions.add(pos)
                    break
            ref = rng.choice(BASES)
            alt_choices = [b for b in BASES if b != ref]
            alt = rng.choice(alt_choices)
            qual = round(rng.uniform(5, 80), 1)
            dp = rng.randint(2, 40)
            af = round(rng.uniform(0.05, 0.95), 3)
            fh.write(
                f"22\t{pos}\t.\t{ref}\t{alt}\t{qual}\tPASS\tDP={dp};AF={af}\n"
            )

    # bgzip + tabix
    subprocess.check_call(
        f"bcftools sort -Oz -o {DATA} {TMP_VCF} && tabix -f -p vcf {DATA}",
        shell=True,
    )

    # Gold: filter to QUAL>=30 && DP>=10
    subprocess.check_call(
        [
            "bcftools", "view", "-e", "QUAL<30 || INFO/DP<10",
            "-Oz", "-o", str(GOLD), str(DATA),
        ]
    )
    subprocess.check_call(["tabix", "-f", "-p", "vcf", str(GOLD)])

    n_total = int(subprocess.check_output(
        f"bcftools view -H {DATA} | wc -l", shell=True, text=True
    ))
    n_gold = int(subprocess.check_output(
        f"bcftools view -H {GOLD} | wc -l", shell=True, text=True
    ))
    print(f"total input records: {n_total}")
    print(f"gold kept records: {n_gold}")


if __name__ == "__main__":
    main()
