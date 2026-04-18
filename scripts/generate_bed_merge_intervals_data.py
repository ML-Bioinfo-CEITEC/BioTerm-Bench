#!/usr/bin/env python3
"""Generate an unsorted BED with overlapping/adjacent intervals + gold merged BED.

Deterministic (seeded). Writes:
  /out/data/intervals.bed  -- 3-column, unsorted, intentionally noisy
  /out/gold/merged.bed      -- 3-column, sorted by (chrom, start),
                               intervals within 50 bp on the same chrom
                               merged into a single interval.
"""
from __future__ import annotations

import random
import subprocess
from pathlib import Path

SEED = 20250418
N_PER_CHROM = 25
CHROMS = ["chr1", "chr2", "chrX"]
MERGE_DIST = 50

DATA = Path("/out/data/intervals.bed")
GOLD = Path("/out/gold/merged.bed")


def main() -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)

    rows: list[tuple[str, int, int]] = []
    for chrom in CHROMS:
        pos = rng.randint(1_000, 5_000)
        for _ in range(N_PER_CHROM):
            length = rng.randint(50, 400)
            # gap: often <= MERGE_DIST (so merges), occasionally larger
            if rng.random() < 0.5:
                gap = rng.randint(-50, MERGE_DIST)  # may overlap
            else:
                gap = rng.randint(MERGE_DIST + 5, 500)
            start = max(0, pos + gap)
            end = start + length
            rows.append((chrom, start, end))
            pos = end

    # Scramble order so the task is not "already sorted".
    rng.shuffle(rows)
    with DATA.open("w") as fh:
        for c, s, e in rows:
            fh.write(f"{c}\t{s}\t{e}\n")

    # Gold: use bedtools (authoritative). Keep it 3-column to avoid
    # surprises (bedtools merge preserves the column count of input).
    sort_cmd = [
        "bash", "-c",
        f"sort -k1,1 -k2,2n {DATA} | bedtools merge -d {MERGE_DIST} -i - > {GOLD}",
    ]
    subprocess.check_call(sort_cmd)

    n_in = sum(1 for _ in DATA.open())
    n_out = sum(1 for _ in GOLD.open())
    print(f"wrote {DATA} ({n_in} input rows) and {GOLD} ({n_out} merged rows)")


if __name__ == "__main__":
    main()
