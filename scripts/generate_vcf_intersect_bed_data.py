#!/usr/bin/env python3
"""Generate a VCF + BED regions file + gold intersected VCF.

Writes:
  /out/data/calls.vcf.gz (+ .tbi)
  /out/data/regions.bed
  /out/gold/in_regions.vcf.gz (+ .tbi)
"""
from __future__ import annotations

import random
import subprocess
from pathlib import Path

SEED = 20250418
N_RECORDS = 400

HEADER = """##fileformat=VCFv4.2
##FILTER=<ID=PASS,Description="All filters passed">
##contig=<ID=22,length=50818468>
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total depth">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO
"""

BASES = "ACGT"
TMP = Path("/tmp/calls.vcf")
DATA_VCF = Path("/out/data/calls.vcf.gz")
DATA_BED = Path("/out/data/regions.bed")
GOLD_VCF = Path("/out/gold/in_regions.vcf.gz")

# Regions are chosen over the same span the variants fall in; roughly
# half of variants should land inside.
REGIONS = [
    ("22", 16_100_000, 16_400_000),
    ("22", 17_200_000, 17_300_000),
    ("22", 18_000_000, 18_500_000),
    ("22", 19_700_000, 19_900_000),
    ("22", 22_000_000, 22_800_000),
]


def main() -> None:
    rng = random.Random(SEED)
    for p in (DATA_VCF, DATA_BED, GOLD_VCF):
        p.parent.mkdir(parents=True, exist_ok=True)

    with TMP.open("w") as fh:
        fh.write(HEADER)
        used: set[int] = set()
        for _ in range(N_RECORDS):
            while True:
                pos = rng.randint(16_000_001, 24_000_000)
                if pos not in used:
                    used.add(pos)
                    break
            ref = rng.choice(BASES)
            alt = rng.choice([b for b in BASES if b != ref])
            qual = round(rng.uniform(20, 80), 1)
            dp = rng.randint(5, 40)
            fh.write(f"22\t{pos}\t.\t{ref}\t{alt}\t{qual}\tPASS\tDP={dp}\n")

    subprocess.check_call(
        f"bcftools sort -Oz -o {DATA_VCF} {TMP} && tabix -f -p vcf {DATA_VCF}",
        shell=True,
    )

    with DATA_BED.open("w") as fh:
        for c, s, e in REGIONS:
            fh.write(f"{c}\t{s}\t{e}\n")

    subprocess.check_call([
        "bcftools", "view", "-R", str(DATA_BED),
        "-Oz", "-o", str(GOLD_VCF), str(DATA_VCF),
    ])
    subprocess.check_call(["tabix", "-f", "-p", "vcf", str(GOLD_VCF)])

    n_total = int(subprocess.check_output(
        f"bcftools view -H {DATA_VCF} | wc -l", shell=True, text=True
    ))
    n_kept = int(subprocess.check_output(
        f"bcftools view -H {GOLD_VCF} | wc -l", shell=True, text=True
    ))
    print(f"input records: {n_total}; kept in regions: {n_kept}")


if __name__ == "__main__":
    main()
