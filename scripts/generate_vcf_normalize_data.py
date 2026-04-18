#!/usr/bin/env python3
"""Generate an un-normalized VCF + gold normalized VCF.

The input VCF intentionally includes:
  - a multi-allelic record (two ALTs on one line),
  - an indel that is NOT left-aligned (same ref as the chromosome
    gives two equivalent representations; we pick the right-most one
    so `bcftools norm` will shift it left).

The gold is produced by `bcftools norm -m -any -f <ref>` so
multi-allelics become separate records and indels are left-aligned.

Writes:
  /out/data/unnorm.vcf.gz (+ .tbi)
  /out/data/ref.fa        (plain fasta + .fai)
  /out/data/ref.fa.fai
  /out/gold/norm.vcf.gz (+ .tbi)
"""
from __future__ import annotations

import gzip
import shutil
import subprocess
from pathlib import Path

REF_GZ = "/opt/references/virus/sars_cov_2.fa.gz"

DATA_DIR = Path("/out/data")
GOLD_DIR = Path("/out/gold")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    ref_fa = DATA_DIR / "ref.fa"
    with gzip.open(REF_GZ, "rt") as src, ref_fa.open("w") as dst:
        shutil.copyfileobj(src, dst)
    subprocess.check_call(["samtools", "faidx", str(ref_fa)])

    # Read the reference sequence so we can pick positions that
    # actually have a run of identical bases (required for
    # left-alignable indels).
    with ref_fa.open() as fh:
        header = fh.readline().strip().lstrip(">").split()[0]
        seq = "".join(line.strip() for line in fh).upper()

    # Find a run of AAA* at least 4 long; we'll right-position an 'A'
    # deletion inside it, which norm will shift to the leftmost 'A'.
    run_start = run_len = None
    i = 0
    while i < len(seq):
        if seq[i] == "A":
            j = i
            while j < len(seq) and seq[j] == "A":
                j += 1
            if j - i >= 4:
                run_start = i
                run_len = j - i
                break
            i = j
        else:
            i += 1
    assert run_start is not None and run_len is not None, "no A-run found"

    # Positions (1-based) of interest
    anchor = run_start  # 0-based; must not be at the beginning
    assert anchor >= 1, "A-run at start; widen"

    # Record 1 (non-left-aligned deletion of one A inside the run):
    #   use POS at the LAST A of the run, REF="TA" ALT="T"
    # where T is the base just before... simpler: just use the a pair
    # (prev_base, last_A) to form REF/ALT. The norm tool then shifts.
    last_A_1b = anchor + run_len         # 1-based last position of run
    prev_base = seq[last_A_1b - 2]       # base just before last A
    record1_pos = last_A_1b - 1          # 1-based position of prev_base
    record1_ref = prev_base + "A"
    record1_alt = prev_base              # i.e. a 1-bp deletion

    # Record 2 (multi-allelic SNP at a far-away position):
    other_pos = run_start + 500 if run_start + 500 < len(seq) - 100 else len(seq) // 2
    while seq[other_pos] == "N":
        other_pos += 1
    record2_pos = other_pos + 1
    record2_ref = seq[other_pos]
    alts = [b for b in "ACGT" if b != record2_ref][:2]

    # Record 3 (simple SNP, already normalized):
    normal_pos = other_pos + 1000
    while seq[normal_pos] == "N":
        normal_pos += 1
    record3_pos = normal_pos + 1
    record3_ref = seq[normal_pos]
    record3_alt = "A" if record3_ref != "A" else "G"

    header_lines = [
        "##fileformat=VCFv4.2",
        f"##contig=<ID={header},length={len(seq)}>",
        "##FILTER=<ID=PASS,Description=\"All filters passed\">",
        "##INFO=<ID=DP,Number=1,Type=Integer,Description=\"depth\">",
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
    ]

    rows = [
        (record1_pos, record1_ref, record1_alt),
        (record2_pos, record2_ref, ",".join(alts)),
        (record3_pos, record3_ref, record3_alt),
    ]
    rows.sort(key=lambda r: r[0])

    tmp = DATA_DIR / "_unnorm.vcf"
    with tmp.open("w") as fh:
        for l in header_lines:
            fh.write(l + "\n")
        for pos, ref, alt in rows:
            fh.write(f"{header}\t{pos}\t.\t{ref}\t{alt}\t50\tPASS\tDP=20\n")

    subprocess.check_call(
        f"bcftools sort -Oz -o {DATA_DIR}/unnorm.vcf.gz {tmp} && "
        f"tabix -f -p vcf {DATA_DIR}/unnorm.vcf.gz",
        shell=True,
    )
    tmp.unlink()

    # Gold = bcftools norm -m -any -f REF  (split multi-allelics AND
    # left-align indels).
    subprocess.check_call([
        "bash", "-c",
        f"bcftools norm -m -any -f {ref_fa} {DATA_DIR}/unnorm.vcf.gz "
        f"| bcftools sort -Oz -o {GOLD_DIR}/norm.vcf.gz - && "
        f"tabix -f -p vcf {GOLD_DIR}/norm.vcf.gz"
    ])

    n_in = int(subprocess.check_output(
        f"bcftools view -H {DATA_DIR}/unnorm.vcf.gz | wc -l",
        shell=True, text=True,
    ))
    n_out = int(subprocess.check_output(
        f"bcftools view -H {GOLD_DIR}/norm.vcf.gz | wc -l",
        shell=True, text=True,
    ))
    print(f"unnormalized records: {n_in}; normalized records: {n_out}")


if __name__ == "__main__":
    main()
