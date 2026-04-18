#!/usr/bin/env python3
"""Generate reads.bam + reference + gold calls.vcf.gz for mpileup-call-snps.

Plants a deterministic set of SNVs into SARS-CoV-2 reads so that
bcftools mpileup + call recovers them robustly.

Writes:
  /out/data/reference.fa.gz (+ .fai, .gzi, + bwa indices)
  /out/data/reads.bam       (+ .bai)
  /out/gold/calls.vcf.gz    (+ .tbi)
"""
from __future__ import annotations

import random
import shutil
import subprocess
from pathlib import Path

import pysam

SRC_REF = "/opt/references/virus/sars_cov_2.fa.gz"
DATA = Path("/out/data")
GOLD = Path("/out/gold")
SEED = 20250418
READ_LEN = 150
COVERAGE = 50  # x


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    GOLD.mkdir(parents=True, exist_ok=True)

    # Copy reference + sidecars so the task is self-contained
    for suffix in ("", ".fai", ".gzi", ".amb", ".ann", ".bwt", ".pac", ".sa"):
        src = Path(SRC_REF + suffix)
        if src.is_file():
            shutil.copy2(src, DATA / ("reference.fa.gz" + suffix))

    fa = pysam.FastaFile(SRC_REF)
    rname = fa.references[0]
    reflen = fa.get_reference_length(rname)
    refseq = fa.fetch(rname).upper()

    rng = random.Random(SEED)

    # Pick 15 planted SNP positions (well-separated, avoid edges)
    planted: dict[int, str] = {}
    while len(planted) < 15:
        p = rng.randint(500, reflen - 500)
        if any(abs(p - q) < 200 for q in planted):
            continue
        ref_base = refseq[p]
        if ref_base == "N":
            continue
        alt = rng.choice([b for b in "ACGT" if b != ref_base])
        planted[p] = alt
    print(f"planted {len(planted)} SNVs: {sorted(planted.items())}")

    # Build a "mutant" reference (in memory) that carries all planted SNVs.
    mutant = list(refseq)
    for p, alt in planted.items():
        mutant[p] = alt
    mutant_seq = "".join(mutant)

    # Simulate reads from the mutant reference; uniform coverage.
    n_reads = max(1, (reflen * COVERAGE) // READ_LEN)
    fastq = DATA.parent / "tmp_reads.fastq"
    with fastq.open("w") as fh:
        for i in range(n_reads):
            pos = rng.randint(0, reflen - READ_LEN - 1)
            seq = mutant_seq[pos : pos + READ_LEN]
            # flip strand half the time
            if rng.random() < 0.5:
                seq = seq.translate(str.maketrans("ACGT", "TGCA"))[::-1]
            qual = "I" * READ_LEN
            fh.write(f"@read_{i:06d}\n{seq}\n+\n{qual}\n")

    # Align with bwa against the original (unmodified) reference; indices
    # were copied above.
    sam = DATA.parent / "tmp_reads.sam"
    subprocess.check_call(
        f"bwa mem -t 2 {DATA / 'reference.fa.gz'} {fastq} > {sam} 2>/dev/null",
        shell=True,
    )
    subprocess.check_call(
        ["samtools", "sort", "-@", "2", "-O", "BAM",
         "-o", str(DATA / "reads.bam"), str(sam)]
    )
    subprocess.check_call(["samtools", "index", str(DATA / "reads.bam")])

    fastq.unlink()
    sam.unlink()

    # Produce gold with the same command the solution uses.
    subprocess.check_call(
        "bcftools mpileup -f {ref} -q 20 -Q 20 --max-depth 1000 {bam} "
        "| bcftools call -mv --ploidy 1 -V indels -Oz -o {vcf}".format(
            ref=DATA / "reference.fa.gz",
            bam=DATA / "reads.bam",
            vcf=GOLD / "calls.vcf.gz",
        ),
        shell=True,
    )
    subprocess.check_call(
        ["tabix", "-f", "-p", "vcf", str(GOLD / "calls.vcf.gz")]
    )

    n_gold = int(subprocess.check_output(
        f"bcftools view -H {GOLD / 'calls.vcf.gz'} | wc -l",
        shell=True, text=True
    ).strip())
    print(f"gold calls: {n_gold}")


if __name__ == "__main__":
    main()
