#!/usr/bin/env python3
"""Generate two synthetic proteomes A and B with known RBH pairs.

Writes:
  /out/data/proteome_a.fa
  /out/data/proteome_b.fa
  /out/gold/rbh.tsv
"""
from __future__ import annotations

import random
from pathlib import Path

SEED = 20260418
AA = "ACDEFGHIKLMNPQRSTVWY"
N_CORE = 6       # orthologous pairs
N_A_ONLY = 4     # A proteins without ortholog in B
N_B_ONLY = 3     # B proteins without ortholog in A
LEN = 220

DATA_A = Path("/out/data/proteome_a.fa")
DATA_B = Path("/out/data/proteome_b.fa")
GOLD = Path("/out/gold/rbh.tsv")


def mutate(seq: str, rate: float, rng: random.Random) -> str:
    out = []
    for c in seq:
        if rng.random() < rate:
            alt = rng.choice(AA.replace(c, ""))
            out.append(alt)
        else:
            out.append(c)
    return "".join(out)


def rand_seq(n: int, rng: random.Random) -> str:
    return "".join(rng.choice(AA) for _ in range(n))


def write_fasta(path: Path, seqs: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for name in sorted(seqs):
            fh.write(f">{name}\n")
            s = seqs[name]
            for i in range(0, len(s), 60):
                fh.write(s[i:i + 60] + "\n")


def main() -> None:
    DATA_A.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)
    seqs_a: dict[str, str] = {}
    seqs_b: dict[str, str] = {}
    rbh: list[tuple[str, str]] = []

    # Core orthologous pairs — same root, ~15% divergence both ways.
    for i in range(N_CORE):
        root = rand_seq(LEN, rng)
        aid = f"A{i+1:03d}"
        bid = f"B{i+1:03d}"
        seqs_a[aid] = mutate(root, 0.10, rng)
        seqs_b[bid] = mutate(root, 0.18, rng)
        rbh.append((aid, bid))

    # A-only proteins — wholly unrelated to anything in B.
    for i in range(N_A_ONLY):
        seqs_a[f"A9{i+1:02d}"] = rand_seq(LEN, rng)
    # B-only
    for i in range(N_B_ONLY):
        seqs_b[f"B9{i+1:02d}"] = rand_seq(LEN, rng)

    write_fasta(DATA_A, seqs_a)
    write_fasta(DATA_B, seqs_b)

    with GOLD.open("w") as fh:
        for a, b in sorted(rbh):
            fh.write(f"{a}\t{b}\n")
    print(f"wrote {DATA_A}, {DATA_B}; RBH pairs={rbh}")


if __name__ == "__main__":
    main()
