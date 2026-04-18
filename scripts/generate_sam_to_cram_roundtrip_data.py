#!/usr/bin/env python3
"""Generate a small coord-sorted BAM + reference copy for the
sam-to-cram-roundtrip task.

Writes:
  /out/data/reads.bam
  /out/data/reads.bam.bai
  /out/data/ref.fa           (plain fasta copy, not gzipped)
  /out/data/ref.fa.fai
  /out/gold/reads.txt        sorted, pipe-joined samtools view output

The gold file is the canonical representation of the BAM's records
(one line per record, tab columns joined with '|' to be robust to
whitespace normalization in diff tools). The agent's CRAM output must
decode back to the same set of records.
"""
from __future__ import annotations

import gzip
import random
import shutil
import subprocess
from pathlib import Path

import pysam

REF_GZ = "/opt/references/virus/sars_cov_2.fa.gz"
SEED = 20250418
N_READS = 300
READ_LEN = 90

DATA_DIR = Path("/out/data")
GOLD_DIR = Path("/out/gold")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    # Write plain (bgzipped would also work; we use plain for simplicity).
    ref_fa = DATA_DIR / "ref.fa"
    with gzip.open(REF_GZ, "rt") as src, ref_fa.open("w") as dst:
        shutil.copyfileobj(src, dst)
    subprocess.check_call(["samtools", "faidx", str(ref_fa)])

    fa = pysam.FastaFile(str(ref_fa))
    refname = fa.references[0]
    reflen = fa.get_reference_length(refname)

    rng = random.Random(SEED)
    sam_path = Path("/tmp/roundtrip.sam")
    with sam_path.open("w") as fh:
        fh.write("@HD\tVN:1.6\tSO:unsorted\n")
        fh.write(f"@SQ\tSN:{refname}\tLN:{reflen}\n")
        fh.write("@PG\tID:bioterm-bench\tPN:bioterm-bench\tVN:0.1\n")
        for i in range(N_READS):
            pos = rng.randint(0, reflen - READ_LEN - 1)
            seq = fa.fetch(refname, pos, pos + READ_LEN).upper().replace("N", "A")
            qual = "I" * READ_LEN
            flag = 0 if rng.random() < 0.85 else 16
            fh.write(f"r{i:05d}\t{flag}\t{refname}\t{pos + 1}\t60\t"
                     f"{READ_LEN}M\t*\t0\t0\t{seq}\t{qual}\n")

    bam_path = DATA_DIR / "reads.bam"
    subprocess.check_call(
        ["samtools", "sort", "-O", "BAM", "-o", str(bam_path), str(sam_path)]
    )
    subprocess.check_call(["samtools", "index", str(bam_path)])

    # Canonical record dump for the grader: only the 11 mandatory SAM
    # columns (QNAME..QUAL), joined with '|' and sorted. Optional
    # tag columns are ignored because CRAM legitimately adds MD/NM.
    dump = subprocess.check_output(
        ["bash", "-c",
         f"samtools view {bam_path} | "
         f"awk -F'\\t' '{{print $1\"|\"$2\"|\"$3\"|\"$4\"|\"$5\"|\"$6\"|\"$7\"|\"$8\"|\"$9\"|\"$10\"|\"$11}}' | "
         f"sort"]
    ).decode()
    (GOLD_DIR / "reads.txt").write_text(dump)

    print(f"wrote {bam_path} ({N_READS} records) and {GOLD_DIR}/reads.txt")


if __name__ == "__main__":
    main()
