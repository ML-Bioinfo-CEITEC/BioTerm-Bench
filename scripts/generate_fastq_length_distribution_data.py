#!/usr/bin/env python3
"""Generate a small gzip FASTQ with varying read lengths + gold histogram.

Deterministic (seeded). Writes:
  /out/data/reads.fastq.gz
  /out/gold/lengths.tsv  (columns: length, count; sorted ascending by length)
"""
from __future__ import annotations

import gzip
import random
from collections import Counter
from pathlib import Path

SEED = 20250418
N_READS = 500
LEN_CHOICES = [50, 75, 100, 125, 150, 200]
LEN_WEIGHTS = [0.05, 0.15, 0.35, 0.2, 0.15, 0.1]

DATA = Path("/out/data/reads.fastq.gz")
GOLD = Path("/out/gold/lengths.tsv")


def main() -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)
    lengths: list[int] = []
    with gzip.open(DATA, "wt") as fh:
        for i in range(N_READS):
            L = rng.choices(LEN_CHOICES, weights=LEN_WEIGHTS, k=1)[0]
            lengths.append(L)
            seq = "".join(rng.choice("ACGT") for _ in range(L))
            qual = "I" * L
            fh.write(f"@read_{i:05d}\n{seq}\n+\n{qual}\n")

    counts = Counter(lengths)
    with GOLD.open("w") as fh:
        fh.write("length\tcount\n")
        for L in sorted(counts):
            fh.write(f"{L}\t{counts[L]}\n")

    print(f"wrote {DATA} ({N_READS} reads), {GOLD} "
          f"({len(counts)} length bins)")


if __name__ == "__main__":
    main()
