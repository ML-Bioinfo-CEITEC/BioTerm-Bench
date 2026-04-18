#!/usr/bin/env python3
"""Generate synthetic chr22 BAM + gold list for the region-extract task.

Deterministic: seeded RNG. Writes:
  /out/data/all_reads.bam  -- sorted + indexed BAM with reads across chr22
  /out/gold/region_read_names.txt -- names of reads overlapping the target
                                     region 22:16000000-17000000

Run inside the base container with the task directory mounted:

    docker run --rm \
        -v "$(pwd)/tasks/region-extract:/out" \
        -v "$(pwd)/scripts:/scripts:ro" \
        bioterm-base:v1 python3 /scripts/generate_region_extract_data.py
"""
from __future__ import annotations

import random
import subprocess
from pathlib import Path

import pysam

REF = "/opt/references/chr22/chr22.fa.gz"
SAM_PATH = Path("/tmp/all_reads.sam")
BAM_PATH = Path("/out/data/all_reads.bam")
GOLD = Path("/out/gold/region_read_names.txt")

SEED = 20250418
N_READS = 400
READ_LEN = 100
REGION_START = 16_000_000
REGION_END = 17_000_000


def main() -> None:
    rng = random.Random(SEED)
    fa = pysam.FastaFile(REF)
    refname = fa.references[0]   # "22"
    reflen = fa.get_reference_length(refname)

    BAM_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    # Pick 400 positions: 40% inside region, 60% outside (gives mix).
    positions: list[int] = []
    for _ in range(N_READS):
        if rng.random() < 0.4:
            pos = rng.randint(REGION_START, REGION_END - READ_LEN - 1)
        else:
            # spread across chr22 avoiding the region
            while True:
                pos = rng.randint(10_500_000, min(reflen - READ_LEN - 1, 50_000_000))
                if pos < REGION_START - READ_LEN or pos > REGION_END:
                    break
        positions.append(pos)

    rng.shuffle(positions)

    with SAM_PATH.open("w") as fh:
        fh.write("@HD\tVN:1.6\tSO:unsorted\n")
        fh.write(f"@SQ\tSN:{refname}\tLN:{reflen}\n")
        fh.write("@PG\tID:bioterm-bench\tPN:bioterm-bench\tVN:0.1\n")

        region_names: list[str] = []
        for i, pos in enumerate(positions):
            seq = fa.fetch(refname, pos, pos + READ_LEN).upper()
            if "N" in seq:
                seq = seq.replace("N", "A")
            qual = "I" * READ_LEN
            name = f"read_{i:05d}"
            flag = 0 if rng.random() < 0.85 else 16
            fh.write(
                f"{name}\t{flag}\t{refname}\t{pos + 1}\t60\t{READ_LEN}M"
                f"\t*\t0\t0\t{seq}\t{qual}\n"
            )
            # Overlap with region_start..region_end inclusive: read spans
            # [pos+1, pos+READ_LEN]. Overlap iff pos+READ_LEN >= REGION_START
            # and pos+1 <= REGION_END.
            aln_start = pos + 1
            aln_end = pos + READ_LEN
            if aln_end >= REGION_START and aln_start <= REGION_END:
                region_names.append(name)

    # Sort + index + convert to BAM in one go via samtools
    subprocess.check_call(
        ["samtools", "sort", "-@", "2", "-O", "BAM", "-o", str(BAM_PATH), str(SAM_PATH)]
    )
    subprocess.check_call(["samtools", "index", str(BAM_PATH)])

    GOLD.write_text("\n".join(sorted(region_names)) + "\n")

    print(f"wrote {BAM_PATH} and {GOLD} ({len(region_names)} reads in region)")


if __name__ == "__main__":
    main()
