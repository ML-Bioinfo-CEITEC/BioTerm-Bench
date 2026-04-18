#!/usr/bin/env python3
"""Generate 5 tiny genomes + 10 k-mers + gold presence grid.

Each "genome" is a 1.5 kb random sequence with a known k-mer spike
planted so the grid has non-trivial structure.
"""
from __future__ import annotations

import random
from pathlib import Path

SEED = 20250418
K = 12
N_GENOMES = 5
GENOME_LEN = 1500

DATA_DIR = Path("/out/data/genomes")
KMERS_PATH = Path("/out/data/kmers.txt")
GOLD = Path("/out/gold/presence.tsv")


def main() -> None:
    rng = random.Random(SEED)

    # Generate 10 target k-mers (random ACGT, length K)
    kmers = sorted({"".join(rng.choices("ACGT", k=K)) for _ in range(20)})[:10]

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    genomes: dict[str, str] = {}
    for i in range(1, N_GENOMES + 1):
        seq = "".join(rng.choices("ACGT", k=GENOME_LEN))
        # Each genome gets a deterministic subset of k-mers spiked in
        idx = [j for j in range(len(kmers)) if (i * 7 + j * 3) % 11 < 5]
        for j in idx:
            pos = rng.randint(100, GENOME_LEN - K - 100)
            seq = seq[:pos] + kmers[j] + seq[pos + K :]
        gid = f"genome_{i:02d}"
        genomes[gid] = seq
        with (DATA_DIR / f"{gid}.fa").open("w") as fh:
            fh.write(f">{gid}\n")
            for p in range(0, len(seq), 70):
                fh.write(seq[p : p + 70] + "\n")

    KMERS_PATH.write_text("\n".join(kmers) + "\n")

    rows: list[tuple[str, str, str]] = []
    for gid in sorted(genomes):
        seq = genomes[gid].upper()
        for k in kmers:
            rows.append((gid, k, "1" if k in seq else "0"))
    rows.sort(key=lambda r: (r[0], r[1]))
    with GOLD.open("w") as fh:
        for r in rows:
            fh.write("\t".join(r) + "\n")

    n_ones = sum(1 for _, _, p in rows if p == "1")
    print(f"wrote {N_GENOMES} genomes + {len(kmers)} kmers; "
          f"{n_ones}/{len(rows)} present rows")


if __name__ == "__main__":
    main()
