#!/usr/bin/env python3
"""Generate fixtures for ortholog-rbh-clusters."""
from __future__ import annotations

import os
import random
from pathlib import Path

SEED = 20260812
AAS = "ACDEFGHIKLMNPQRSTVWY"


def out_root() -> Path:
    return Path(os.environ.get("BIOTERM_OUT_ROOT", "/out"))


def rand_protein(n: int, rng: random.Random) -> str:
    return "".join(rng.choice(AAS) for _ in range(n))


def mutate(seq: str, rate: float, rng: random.Random) -> str:
    out = []
    for aa in seq:
        if rng.random() < rate:
            out.append(rng.choice(AAS.replace(aa, "")))
        else:
            out.append(aa)
    return "".join(out)


def write_fasta(path: Path, records: list[tuple[str, str]]) -> None:
    with path.open("w") as fh:
        for name, seq in records:
            fh.write(f">{name}\n")
            for i in range(0, len(seq), 60):
                fh.write(seq[i:i + 60] + "\n")


def greedy_keep(triplets: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    used: set[str] = set()
    kept: list[tuple[str, str, str]] = []
    for triplet in sorted(triplets):
        if any(protein in used for protein in triplet):
            continue
        kept.append(triplet)
        used.update(triplet)
    return kept


def main() -> None:
    root = out_root()
    data_dir = root / "data"
    gold_dir = root / "gold"
    data_dir.mkdir(parents=True, exist_ok=True)
    gold_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)

    ancestors = {
        f"G{i:02d}": rand_protein(115 + (i % 3) * 8, rng)
        for i in range(1, 7)
    }

    species_a: list[tuple[str, str]] = []
    species_b: list[tuple[str, str]] = []
    species_c: list[tuple[str, str]] = []
    clusters: list[tuple[str, str, str]] = []

    for group in ["G01", "G02", "G03", "G04", "G05"]:
        anc = ancestors[group]
        a_id = f"A_{group}"
        b_id = f"B_{group}"
        c_id = f"C_{group}"
        species_a.append((a_id, mutate(anc, 0.07, rng)))
        species_b.append((b_id, mutate(anc, 0.09, rng)))
        species_c.append((c_id, mutate(anc, 0.11, rng)))
        clusters.append((a_id, b_id, c_id))

    # Incomplete family: should not appear in the final clusters.
    species_a.append(("A_G06", mutate(ancestors["G06"], 0.06, rng)))
    species_b.append(("B_G06", mutate(ancestors["G06"], 0.08, rng)))

    # Within-species paralogs / distractors.
    species_a.append(("A_G03_dup", mutate(species_a[2][1], 0.22, rng)))
    species_b.append(("B_G02_dup", mutate(species_b[1][1], 0.20, rng)))
    species_c.append(("C_G05_dup", mutate(species_c[4][1], 0.23, rng)))

    # Competing tied-best family that creates overlapping valid triplets.
    bridge_anc = rand_protein(129, rng)
    bridge_a = mutate(bridge_anc, 0.06, rng)
    bridge_b = mutate(bridge_anc, 0.06, rng)
    bridge_c = mutate(bridge_anc, 0.06, rng)
    species_a.append(("A_G04_bridge", bridge_a))
    species_b.append(("B_G04_bridge", bridge_b))
    species_b.append(("B_G04_bridge_alt", bridge_b))
    species_c.append(("C_G04_bridge", bridge_c))
    species_c.append(("C_G04_bridge_alt", bridge_c))

    competing = [
        ("A_G04_bridge", "B_G04_bridge", "C_G04_bridge"),
        ("A_G04_bridge", "B_G04_bridge", "C_G04_bridge_alt"),
        ("A_G04_bridge", "B_G04_bridge_alt", "C_G04_bridge"),
        ("A_G04_bridge", "B_G04_bridge_alt", "C_G04_bridge_alt"),
    ]
    kept = greedy_keep(competing)
    assert kept == [("A_G04_bridge", "B_G04_bridge", "C_G04_bridge")]
    clusters.extend(kept)

    # Orphans.
    for prefix, bucket in [("A", species_a), ("B", species_b), ("C", species_c)]:
        bucket.append((f"{prefix}_ORPHAN1", rand_protein(124, rng)))
        bucket.append((f"{prefix}_ORPHAN2", rand_protein(132, rng)))

    write_fasta(data_dir / "species_a.fa", species_a)
    write_fasta(data_dir / "species_b.fa", species_b)
    write_fasta(data_dir / "species_c.fa", species_c)

    with (gold_dir / "clusters.tsv").open("w") as fh:
        for triplet in sorted(clusters):
            fh.write("\t".join(triplet) + "\n")

    print(
        "wrote proteomes with "
        f"{len(species_a)}/{len(species_b)}/{len(species_c)} proteins and "
        f"{len(clusters)} gold RBH clusters; competing_triplets={len(competing)}"
    )


if __name__ == "__main__":
    main()
