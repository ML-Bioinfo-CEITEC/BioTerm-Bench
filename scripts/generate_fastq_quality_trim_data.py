#!/usr/bin/env python3
"""Generate a gzipped FASTQ with quality-trimmable tails + gold stats.

Writes:
  /out/data/reads.fastq.gz
  /out/gold/stats.json
"""
from __future__ import annotations

import gzip
import json
import random
from pathlib import Path

SEED = 20260418
N_READS = 1000
READ_LEN = 100
Q_THR = 20  # Phred threshold used by the instruction
DATA = Path("/out/data/reads.fastq.gz")
GOLD = Path("/out/gold/stats.json")

BASES = "ACGT"


def _qchar(q: int) -> str:
    return chr(min(max(q, 0), 40) + 33)


def _trim(quals: list[int]) -> int:
    """Return trimmed length given per-base Phred qualities."""
    n = len(quals)
    i = n
    while i > 0 and quals[i - 1] < Q_THR:
        i -= 1
    return i


def main() -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)

    bases_in = 0
    bases_out = 0
    n_out = 0
    sum_len_in = 0
    sum_len_out = 0

    with gzip.open(DATA, "wt") as fh:
        for i in range(1, N_READS + 1):
            seq = "".join(rng.choice(BASES) for _ in range(READ_LEN))
            # build a quality profile: mid-read quals 25..38, with a
            # tail of decreasing quality. Deterministic randomness.
            qs = [rng.randint(28, 38) for _ in range(READ_LEN)]
            # Pick a tail length where quals decay below 20
            tail = rng.randint(0, 60)
            for k in range(tail):
                idx = READ_LEN - 1 - k
                if idx < 0:
                    break
                qs[idx] = max(0, rng.randint(5, 19))
            # occasional all-bad read (should be dropped)
            if i % 97 == 0:
                qs = [rng.randint(2, 15) for _ in range(READ_LEN)]

            qstr = "".join(_qchar(q) for q in qs)
            fh.write(f"@read_{i:05d}\n{seq}\n+\n{qstr}\n")

            bases_in += READ_LEN
            sum_len_in += READ_LEN
            new_len = _trim(qs)
            if new_len > 0:
                n_out += 1
                bases_out += new_len
                sum_len_out += new_len

    mean_in = sum_len_in / N_READS
    mean_out = (sum_len_out / n_out) if n_out else 0.0

    gold = {
        "n_in": N_READS,
        "n_out": n_out,
        "bases_in": bases_in,
        "bases_out": bases_out,
        "mean_len_in": round(mean_in, 4),
        "mean_len_out": round(mean_out, 4),
    }
    GOLD.write_text(json.dumps(gold, indent=2, sort_keys=True) + "\n")
    print(f"wrote {DATA} and {GOLD}; gold={gold}")


if __name__ == "__main__":
    main()
