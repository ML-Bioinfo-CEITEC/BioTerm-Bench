#!/usr/bin/env python3
"""Generate a mixed SNV/indel VCF and two gold splits.

Writes:
  /out/data/variants.vcf.gz  (+ .tbi)
  /out/gold/snps.vcf.gz      (+ .tbi)
  /out/gold/indels.vcf.gz    (+ .tbi)
"""
from __future__ import annotations

import random
import subprocess
from pathlib import Path

SEED = 20250418
N_RECORDS = 400
FRAC_SNPS = 0.6

BASES = "ACGT"
TMP_VCF = Path("/tmp/variants.vcf")
DATA = Path("/out/data/variants.vcf.gz")
GOLD_SNPS = Path("/out/gold/snps.vcf.gz")
GOLD_INDELS = Path("/out/gold/indels.vcf.gz")

HEADER = """##fileformat=VCFv4.2
##FILTER=<ID=PASS,Description="All filters passed">
##contig=<ID=22,length=50818468>
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total depth">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO
"""


def main() -> None:
    rng = random.Random(SEED)
    DATA.parent.mkdir(parents=True, exist_ok=True)
    GOLD_SNPS.parent.mkdir(parents=True, exist_ok=True)

    with TMP_VCF.open("w") as fh:
        fh.write(HEADER)
        used_positions: set[int] = set()
        for _ in range(N_RECORDS):
            while True:
                pos = rng.randint(16_000_001, 16_000_000 + 10_000_000)
                if pos not in used_positions:
                    used_positions.add(pos)
                    break
            if rng.random() < FRAC_SNPS:
                ref = rng.choice(BASES)
                alt = rng.choice([b for b in BASES if b != ref])
            else:
                if rng.random() < 0.5:
                    # insertion
                    ref = rng.choice(BASES)
                    ins_len = rng.randint(1, 4)
                    alt = ref + "".join(rng.choices(BASES, k=ins_len))
                else:
                    # deletion
                    del_len = rng.randint(1, 4)
                    ref = "".join(rng.choices(BASES, k=1 + del_len))
                    alt = ref[0]
            dp = rng.randint(10, 50)
            qual = round(rng.uniform(30, 80), 1)
            fh.write(f"22\t{pos}\t.\t{ref}\t{alt}\t{qual}\tPASS\tDP={dp}\n")

    subprocess.check_call(
        f"bcftools sort -Oz -o {DATA} {TMP_VCF} && tabix -f -p vcf {DATA}",
        shell=True,
    )
    for out, kind in [(GOLD_SNPS, "snps"), (GOLD_INDELS, "indels")]:
        subprocess.check_call(
            ["bcftools", "view", "-v", kind, "-Oz", "-o", str(out), str(DATA)]
        )
        subprocess.check_call(["tabix", "-f", "-p", "vcf", str(out)])

    for p in (DATA, GOLD_SNPS, GOLD_INDELS):
        n = int(subprocess.check_output(
            f"bcftools view -H {p} | wc -l", shell=True, text=True
        ).strip())
        print(f"  {p.name}: {n} records")


if __name__ == "__main__":
    main()
