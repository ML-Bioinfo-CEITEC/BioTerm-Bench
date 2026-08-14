#!/usr/bin/env python3
"""Generate sequences.fa + gold stats.tsv for seqkit-fasta-stats.

Deterministic: seeded RNG. Produces 6 sequences of different lengths
and varying GC / N content, including one sequence with no Ns.
"""
from __future__ import annotations

import random
import textwrap
from pathlib import Path

OUT_DATA = Path("/out/data")
OUT_GOLD = Path("/out/gold")

SEED = 20250418


def make_seq(rng: random.Random, length: int, gc: float, n_frac: float) -> str:
    chars = []
    for _ in range(length):
        r = rng.random()
        if r < n_frac:
            chars.append("N")
        else:
            if rng.random() < gc:
                chars.append(rng.choice("GC"))
            else:
                chars.append(rng.choice("AT"))
    return "".join(chars)


def main() -> None:
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    OUT_GOLD.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)

    specs = [
        ("seq_A", 500, 0.50, 0.00),
        ("seq_B", 1200, 0.65, 0.01),
        ("seq_C", 750, 0.35, 0.05),
        ("seq_D", 2400, 0.55, 0.00),
        ("seq_E", 300, 0.48, 0.10),
        ("seq_F", 150, 0.60, 0.00),
    ]
    records = [(sid, make_seq(rng, n, gc, nf)) for sid, n, gc, nf in specs]

    fa_lines = []
    for sid, seq in records:
        fa_lines.append(f">{sid} extra description goes here")
        fa_lines.extend(textwrap.wrap(seq, 70))
    (OUT_DATA / "sequences.fa").write_text("\n".join(fa_lines) + "\n")

    tsv = ["seq_id\tlength\tgc_percent\tn_percent"]
    for sid, seq in records:
        length = len(seq)
        u = seq.upper()
        gc_pct = 100.0 * (u.count("G") + u.count("C")) / length
        n_pct = 100.0 * u.count("N") / length
        tsv.append(f"{sid}\t{length}\t{gc_pct:.2f}\t{n_pct:.2f}")
    (OUT_GOLD / "stats.tsv").write_text("\n".join(tsv) + "\n")

    print(f"wrote sequences.fa ({len(records)} records), gold stats.tsv")
    print("  rows:")
    for row in tsv[1:]:
        print("   ", row)


if __name__ == "__main__":
    main()
