#!/usr/bin/env python3
"""Generate synthetic unsorted SAM input for the bam-sort-index task.

Deterministic: seeded RNG, ordered reference access. Produces
``unsorted.sam`` with 200 single-end reads of length 100 drawn from the
SARS-CoV-2 reference baked into the base image, in a shuffled order so
the file is genuinely unsorted.

Run inside the base container with the task data/ directory mounted:

    docker run --rm -v "$(pwd)/tasks/bam-sort-index/data:/out" \
        bioterm-base:v1 python3 /scripts/generate_bam_sort_index_data.py
"""
from __future__ import annotations

import random
from pathlib import Path

import pysam

OUT_SAM = Path("/out/unsorted.sam")
REF = "/opt/references/virus/sars_cov_2.fa.gz"
SEED = 20250418
N_READS = 200
READ_LEN = 100


def main() -> None:
    rng = random.Random(SEED)
    fa = pysam.FastaFile(REF)
    refname = fa.references[0]
    reflen = fa.get_reference_length(refname)

    records: list[tuple[str, int, int, str, str]] = []
    for i in range(N_READS):
        pos = rng.randint(0, reflen - READ_LEN - 1)
        seq = fa.fetch(refname, pos, pos + READ_LEN).upper()
        if "N" in seq:
            seq = seq.replace("N", "A")
        qual = "I" * READ_LEN
        read_name = f"read_{i:05d}"
        flag = 0 if rng.random() < 0.85 else 16  # mix of forward/reverse
        records.append((read_name, flag, pos + 1, seq, qual))

    rng.shuffle(records)

    OUT_SAM.parent.mkdir(parents=True, exist_ok=True)
    with OUT_SAM.open("w") as fh:
        fh.write("@HD\tVN:1.6\tSO:unsorted\n")
        fh.write(f"@SQ\tSN:{refname}\tLN:{reflen}\n")
        fh.write("@PG\tID:bioterm-bench\tPN:bioterm-bench\tVN:0.1\n")
        for name, flag, pos, seq, qual in records:
            fh.write(
                f"{name}\t{flag}\t{refname}\t{pos}\t60\t{READ_LEN}M\t*\t0\t0\t{seq}\t{qual}\n"
            )

    print(f"wrote {OUT_SAM} ({N_READS} records)")


if __name__ == "__main__":
    main()
