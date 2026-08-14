#!/usr/bin/env python3
"""Generate a paired-end BAM with a known insert-size distribution.

The insert sizes are drawn from a normal distribution with fixed mean
and stdev, so the agent's reported numbers should match ours closely.

Writes:
  /out/data/reads.bam
  /out/data/reads.bam.bai
  /out/gold/insert.json   {"mean", "median", "stdev", "*_tol"}
"""
from __future__ import annotations

import json
import random
import statistics
import subprocess
from pathlib import Path

import pysam

REF = "/opt/references/virus/sars_cov_2.fa.gz"
SEED = 20250418
N_PAIRS = 300
READ_LEN = 80
INSERT_MEAN = 350.0
INSERT_STDEV = 60.0

DATA = Path("/out/data/reads.bam")
GOLD = Path("/out/gold/insert.json")


def main() -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)
    fa = pysam.FastaFile(REF)
    rname = fa.references[0]
    reflen = fa.get_reference_length(rname)

    def grab(pos: int) -> str:
        return fa.fetch(rname, pos, pos + READ_LEN).upper().replace("N", "A")

    sam = ["@HD\tVN:1.6\tSO:unsorted\n",
           f"@SQ\tSN:{rname}\tLN:{reflen}\n",
           "@PG\tID:bioterm-bench\tPN:bioterm-bench\tVN:0.1\n"]

    inserts: list[int] = []
    for i in range(N_PAIRS):
        L = max(READ_LEN + 20, int(round(rng.gauss(INSERT_MEAN, INSERT_STDEV))))
        inserts.append(L)
        p1 = rng.randint(0, reflen - L - READ_LEN - 1)
        p2 = p1 + L - READ_LEN
        tlen = L
        seq1 = grab(p1)
        seq2 = grab(p2)
        qual = "I" * READ_LEN
        sam.append(
            f"p_{i:05d}\t99\t{rname}\t{p1 + 1}\t60\t{READ_LEN}M\t=\t"
            f"{p2 + 1}\t{tlen}\t{seq1}\t{qual}\n"
        )
        sam.append(
            f"p_{i:05d}\t147\t{rname}\t{p2 + 1}\t60\t{READ_LEN}M\t=\t"
            f"{p1 + 1}\t{-tlen}\t{seq2}\t{qual}\n"
        )

    sam_path = Path("/tmp/isize.sam")
    sam_path.write_text("".join(sam))
    subprocess.check_call(
        ["samtools", "sort", "-O", "BAM", "-o", str(DATA), str(sam_path)]
    )
    subprocess.check_call(["samtools", "index", str(DATA)])

    # Use samtools stats as the authority for the gold values.
    stats = subprocess.check_output(
        ["samtools", "stats", str(DATA)], text=True
    )
    mean = stdev = None
    for line in stats.splitlines():
        if line.startswith("SN\tinsert size average:"):
            mean = float(line.split("\t")[2])
        elif line.startswith("SN\tinsert size standard deviation:"):
            stdev = float(line.split("\t")[2])

    gold = {
        "mean_insert":  mean,
        "stdev_insert": stdev,
        # Agents may round to fewer decimals; give an absolute tol
        # that still catches "wrong insert-size source" mistakes.
        "mean_insert_tol":  1.0,
        "stdev_insert_tol": 3.0,
    }
    GOLD.write_text(json.dumps(gold, indent=2, sort_keys=True) + "\n")
    print(f"wrote {DATA} and gold={gold}")


if __name__ == "__main__":
    main()
