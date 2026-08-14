#!/usr/bin/env python3
"""Generate several small genomes + gold pairwise Jaccard matrix.

Writes:
  /out/data/genomes/genome_*.fa
  /out/gold/jaccard.tsv
"""
from __future__ import annotations

import random
from pathlib import Path

SEED = 20260418
N_GENOMES = 6
K = 15
LEN = 3000
DATA_DIR = Path("/out/data/genomes")
GOLD = Path("/out/gold/jaccard.tsv")
BASES = "ACGT"


def rand_seq(n: int, rng: random.Random) -> str:
    return "".join(rng.choice(BASES) for _ in range(n))


def mutate(seq: str, rate: float, rng: random.Random) -> str:
    out = []
    for c in seq:
        if rng.random() < rate:
            out.append(rng.choice(BASES.replace(c, "")))
        else:
            out.append(c)
    return "".join(out)


def kmers_canonical(seq: str, k: int) -> set[str]:
    comp = str.maketrans("ACGT", "TGCA")
    out = set()
    s = seq.upper()
    n = len(s)
    for i in range(n - k + 1):
        w = s[i:i + k]
        if any(b not in "ACGT" for b in w):
            continue
        rc = w.translate(comp)[::-1]
        out.add(min(w, rc))
    return out


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)

    genomes: dict[str, str] = {}
    root = rand_seq(LEN, rng)
    # Two clusters of related genomes:
    #  - genome_01, 02, 03 share a root (~5-15% divergence)
    #  - genome_04, 05 share a different root
    #  - genome_06 is wholly independent
    root_a = root
    root_b = rand_seq(LEN, rng)

    genomes["genome_01"] = mutate(root_a, 0.02, rng)
    genomes["genome_02"] = mutate(root_a, 0.08, rng)
    genomes["genome_03"] = mutate(root_a, 0.15, rng)
    genomes["genome_04"] = mutate(root_b, 0.03, rng)
    genomes["genome_05"] = mutate(root_b, 0.12, rng)
    genomes["genome_06"] = rand_seq(LEN, rng)

    assert len(genomes) == N_GENOMES

    for name, seq in genomes.items():
        p = DATA_DIR / f"{name}.fa"
        with p.open("w") as fh:
            fh.write(f">{name}\n")
            for i in range(0, len(seq), 60):
                fh.write(seq[i:i + 60] + "\n")

    # Gold matrix: half-matrix in deterministic order.
    ids = sorted(genomes)
    kmer_sets = {g: kmers_canonical(genomes[g], K) for g in ids}

    rows: list[str] = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            inter = len(kmer_sets[a] & kmer_sets[b])
            union = len(kmer_sets[a] | kmer_sets[b])
            j_val = inter / union if union else 0.0
            rows.append(f"{a}\t{b}\t{round(j_val, 6):.6f}")

    with GOLD.open("w") as fh:
        fh.write("\n".join(rows) + "\n")
    print(f"wrote {N_GENOMES} genomes and {len(rows)} Jaccard rows")


if __name__ == "__main__":
    main()
