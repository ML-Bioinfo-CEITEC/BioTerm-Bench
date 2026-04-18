#!/usr/bin/env python3
"""Generate multi-record FASTA + gold sliding-window GC TSV.

Writes:
  /out/data/seqs.fa
  /out/gold/gc_windows.tsv
"""
from __future__ import annotations

import random
from pathlib import Path

SEED = 20260418
N_SEQS = 8
DATA = Path("/out/data/seqs.fa")
GOLD = Path("/out/gold/gc_windows.tsv")

WIN = 100
STEP = 50
BASES = "ACGT"


def gc_pct(window: str) -> float:
    w = window.upper()
    gc = sum(1 for b in w if b in "GC")
    return round(100.0 * gc / len(w), 2) if w else 0.0


def main() -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)
    lengths = [250, 300, 500, 750, 1000, 1200, 450, 620]
    assert len(lengths) == N_SEQS

    rows: list[str] = []
    with DATA.open("w") as fh:
        for i, L in enumerate(lengths, start=1):
            # Vary background GC per sequence so windows differ
            gc_bias = 0.3 + 0.05 * i
            seq = "".join(
                rng.choices(
                    BASES,
                    weights=[(1 - gc_bias) / 2, gc_bias / 2,
                             gc_bias / 2, (1 - gc_bias) / 2],
                )[0]
                for _ in range(L)
            )
            # mixed case to exercise upper-casing
            if i % 2 == 0:
                seq = seq.lower()

            fh.write(f">seq_{i:02d}\n")
            for j in range(0, len(seq), 60):
                fh.write(seq[j:j + 60] + "\n")

            s = seq.upper()
            for start in range(0, len(s) - WIN + 1, STEP):
                end = start + WIN
                gp = gc_pct(s[start:end])
                rows.append(f"seq_{i:02d}\t{start}\t{end}\t{gp:.2f}")

    with GOLD.open("w") as fh:
        fh.write("\n".join(rows) + "\n")
    print(f"wrote {DATA} and {GOLD}; {len(rows)} rows")


if __name__ == "__main__":
    main()
