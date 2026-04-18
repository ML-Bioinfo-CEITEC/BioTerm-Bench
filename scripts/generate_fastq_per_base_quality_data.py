#!/usr/bin/env python3
"""Generate a single-end gzipped FASTQ with varying read lengths and
position-dependent quality decay.

Writes:
  /out/data/reads.fastq.gz
  /out/gold/per_base_quality.tsv
"""
from __future__ import annotations

import gzip
import random
from pathlib import Path

import numpy as np

SEED = 20260418
DATA = Path("/out/data/reads.fastq.gz")
GOLD = Path("/out/gold/per_base_quality.tsv")

N_READS = 300
LEN_MIN = 40
LEN_MAX = 150


def main() -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)
    np_rng = np.random.default_rng(SEED)

    # Per-position quality distribution: baseline 36 decaying to 18 at len 150,
    # with gaussian noise.
    def draw_quality(length: int) -> list[int]:
        out = []
        for pos in range(length):
            decay = 36 - 16 * (pos / (LEN_MAX - 1))
            q = int(round(np_rng.normal(decay, 3.0)))
            q = max(2, min(40, q))
            out.append(q)
        return out

    # Record per-position quality samples for the gold table
    per_pos: dict[int, list[int]] = {}
    lines: list[str] = []
    for i in range(N_READS):
        length = rng.randint(LEN_MIN, LEN_MAX)
        seq = "".join(rng.choices("ACGT", k=length))
        qual = draw_quality(length)
        qual_str = "".join(chr(q + 33) for q in qual)
        lines.append(f"@read_{i:05d}")
        lines.append(seq)
        lines.append("+")
        lines.append(qual_str)
        for pos, q in enumerate(qual):
            per_pos.setdefault(pos, []).append(q)

    with gzip.open(DATA, "wt") as fh:
        fh.write("\n".join(lines) + "\n")

    out = ["pos\tn\tmean_q\tmedian_q"]
    for pos in sorted(per_pos):
        vals = per_pos[pos]
        n = len(vals)
        mean_q = float(np.mean(vals))
        median_q = float(np.percentile(vals, 50.0))
        out.append(f"{pos}\t{n}\t{mean_q:.4f}\t{median_q:.4f}")

    GOLD.write_text("\n".join(out) + "\n")
    print(f"wrote {DATA} with {N_READS} reads; gold has {len(per_pos)} positions")


if __name__ == "__main__":
    main()
