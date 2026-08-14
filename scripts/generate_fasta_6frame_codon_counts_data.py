#!/usr/bin/env python3
"""Generate a synthetic multi-FASTA + gold 6-frame codon count TSV.

Writes:
  /out/data/seqs.fa
  /out/gold/codon_counts.tsv
"""
from __future__ import annotations

import random
from pathlib import Path

SEED = 20260418
N_SEQS = 12
MIN_LEN, MAX_LEN = 300, 1500
DATA = Path("/out/data/seqs.fa")
GOLD = Path("/out/gold/codon_counts.tsv")

BASES = "ACGT"
COMP = {"A": "T", "C": "G", "G": "C", "T": "A", "N": "N"}


def revcomp(s: str) -> str:
    return "".join(COMP.get(b, "N") for b in reversed(s))


def count_codons(seq: str) -> dict[str, int]:
    out: dict[str, int] = {a + b + c: 0 for a in BASES for b in BASES for c in BASES}
    n = len(seq)
    for frame in (0, 1, 2):
        i = frame
        while i + 3 <= n:
            cod = seq[i:i + 3]
            if cod in out:
                out[cod] += 1
            i += 3
    return out


def main() -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)
    totals: dict[str, int] = {a + b + c: 0 for a in BASES for b in BASES for c in BASES}

    with DATA.open("w") as fh:
        for i in range(1, N_SEQS + 1):
            n = rng.randint(MIN_LEN, MAX_LEN)
            seq = "".join(rng.choice(BASES) for _ in range(n))
            # splatter a few Ns to exercise filtering
            for _ in range(rng.randint(0, 5)):
                pos = rng.randint(0, n - 1)
                seq = seq[:pos] + "N" + seq[pos + 1:]
            # mixed case to exercise upper-casing
            if i % 3 == 0:
                seq = seq.lower()
            fh.write(f">seq_{i:03d}\n")
            for j in range(0, len(seq), 60):
                fh.write(seq[j:j + 60] + "\n")

            su = seq.upper()
            rc = revcomp(su)
            for strand in (su, rc):
                for cod, c in count_codons(strand).items():
                    totals[cod] += c

    with GOLD.open("w") as fh:
        for cod in sorted(totals):
            fh.write(f"{cod}\t{totals[cod]}\n")
    print(f"wrote {DATA} and {GOLD}; total={sum(totals.values())}")


if __name__ == "__main__":
    main()
