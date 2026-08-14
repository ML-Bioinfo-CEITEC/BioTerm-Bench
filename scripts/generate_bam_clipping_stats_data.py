#!/usr/bin/env python3
"""Generate a coord-sorted, paired-end BAM with deliberate soft-clip patterns.

Writes:
  /out/data/reads.bam
  /out/data/reads.bam.bai
  /out/gold/stats.json

Soft-clips are introduced on a deterministic subset of reads by
rewriting the CIGAR to include leading / trailing S operations. Gold
numbers are derived from the *same* CIGAR logic an honest agent would
use: left_clip = leading S run, right_clip = trailing S run; totals and
percentile computed directly.
"""
from __future__ import annotations

import json
import random
import re
import subprocess
from pathlib import Path

import numpy as np
import pysam

REF = "/opt/references/virus/sars_cov_2.fa.gz"
SEED = 20260418
N_PAIRS = 120
READ_LEN = 80
INSERT = 240

DATA = Path("/out/data/reads.bam")
GOLD = Path("/out/gold/stats.json")

CIGAR_RE = re.compile(r"(\d+)([MIDNSHP=X])")


def _clips_from_cigar(cigar: str) -> tuple[int, int]:
    ops = CIGAR_RE.findall(cigar)
    left = int(ops[0][0]) if ops and ops[0][1] == "S" else 0
    right = int(ops[-1][0]) if ops and ops[-1][1] == "S" else 0
    return left, right


def main() -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)
    fa = pysam.FastaFile(REF)
    rname = fa.references[0]
    reflen = fa.get_reference_length(rname)

    def grab(pos: int, length: int) -> str:
        s = fa.fetch(rname, pos, pos + length).upper()
        return s.replace("N", "A")

    sam: list[str] = [
        "@HD\tVN:1.6\tSO:unsorted\n",
        f"@SQ\tSN:{rname}\tLN:{reflen}\n",
        "@PG\tID:bioterm-bench\tPN:bioterm-bench\tVN:0.1\n",
    ]

    cigars_all: list[str] = []
    for i in range(N_PAIRS):
        p1 = rng.randint(10, reflen - INSERT - READ_LEN - 10)
        p2 = p1 + INSERT - READ_LEN

        # deterministic clip pattern
        r = rng.random()
        if r < 0.45:
            c1, c2 = f"{READ_LEN}M", f"{READ_LEN}M"
        elif r < 0.65:
            k = rng.randint(3, 15)
            c1 = f"{k}S{READ_LEN - k}M"
            c2 = f"{READ_LEN}M"
        elif r < 0.80:
            k = rng.randint(3, 15)
            c1 = f"{READ_LEN}M"
            c2 = f"{READ_LEN - k}M{k}S"
        elif r < 0.90:
            k1 = rng.randint(3, 10)
            k2 = rng.randint(3, 10)
            c1 = f"{k1}S{READ_LEN - k1 - k2}M{k2}S"
            c2 = f"{READ_LEN}M"
        else:
            k1 = rng.randint(2, 8)
            k2 = rng.randint(2, 8)
            c1 = f"{k1}S{READ_LEN - k1}M"
            c2 = f"{READ_LEN - k2}M{k2}S"

        seq1 = grab(p1, READ_LEN)
        seq2 = grab(p2, READ_LEN)
        qual = "I" * READ_LEN
        tlen = p2 + READ_LEN - p1
        sam.append(
            f"pair_{i:04d}\t99\t{rname}\t{p1 + 1}\t60\t{c1}\t=\t{p2 + 1}"
            f"\t{tlen}\t{seq1}\t{qual}\n"
        )
        sam.append(
            f"pair_{i:04d}\t147\t{rname}\t{p2 + 1}\t60\t{c2}\t=\t{p1 + 1}"
            f"\t{-tlen}\t{seq2}\t{qual}\n"
        )
        cigars_all.extend([c1, c2])

    raw = Path("/tmp/raw.sam")
    raw.write_text("".join(sam))

    subprocess.check_call([
        "bash", "-c",
        f"samtools sort -O bam -o {DATA} {raw}"
    ])
    subprocess.check_call(["samtools", "index", str(DATA)])

    totals = []
    with_clip = 0
    for c in cigars_all:
        lc, rc = _clips_from_cigar(c)
        t = lc + rc
        totals.append(t)
        if t > 0:
            with_clip += 1

    n = len(totals)
    mean_total = float(np.mean(totals)) if n else 0.0
    clipped_totals = [t for t in totals if t > 0]
    p90 = float(np.percentile(clipped_totals, 90)) if clipped_totals else 0.0

    gold = {
        "n_primary_mapped": n,
        "n_with_any_clip": with_clip,
        "mean_total_clip": round(mean_total, 4),
        "p90_total_clip": round(p90, 4),
    }
    GOLD.write_text(json.dumps(gold, indent=2, sort_keys=True) + "\n")
    print(f"wrote {DATA} gold={gold}")


if __name__ == "__main__":
    main()
