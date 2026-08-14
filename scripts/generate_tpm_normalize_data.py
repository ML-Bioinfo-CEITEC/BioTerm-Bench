#!/usr/bin/env python3
"""Generate counts.tsv, gene_lengths.tsv and the gold TPM matrix.

Deterministic: seeded RNG. Produces 20 genes x 4 samples.
"""
from __future__ import annotations

import random
from pathlib import Path

import pandas as pd

SEED = 20250418
N_GENES = 20
N_SAMPLES = 4

DATA = Path("/out/data")
GOLD = Path("/out/gold")


def main() -> None:
    rng = random.Random(SEED)
    DATA.mkdir(parents=True, exist_ok=True)
    GOLD.mkdir(parents=True, exist_ok=True)

    gene_ids = [f"ENSG{i:08d}" for i in range(1, N_GENES + 1)]
    lengths = [rng.randint(300, 10_000) for _ in gene_ids]

    samples = [f"sample_{j}" for j in range(1, N_SAMPLES + 1)]
    counts = {}
    for s in samples:
        # Sprinkle zeros + a long right tail
        vals = []
        for _ in gene_ids:
            if rng.random() < 0.1:
                vals.append(0)
            else:
                vals.append(int(rng.lognormvariate(3.5, 1.4)))
        counts[s] = vals

    df_counts = pd.DataFrame({"gene_id": gene_ids, **counts})
    df_counts.to_csv(DATA / "counts.tsv", sep="\t", index=False)
    df_lengths = pd.DataFrame({"gene_id": gene_ids, "length_bp": lengths})
    df_lengths.to_csv(DATA / "gene_lengths.tsv", sep="\t", index=False)

    lens = pd.Series(lengths, index=gene_ids)
    tpm = df_counts.copy()
    for s in samples:
        rpk = df_counts[s] / (lens.loc[df_counts["gene_id"]].values / 1000.0)
        scale = rpk.sum() / 1_000_000
        tpm[s] = rpk / scale
    tpm.to_csv(GOLD / "tpm.tsv", sep="\t", index=False, float_format="%.6f")

    print(f"wrote counts.tsv ({N_GENES} genes x {N_SAMPLES} samples), "
          f"gene_lengths.tsv, gold tpm.tsv")
    print("column sums:", {s: float(tpm[s].sum()) for s in samples})


if __name__ == "__main__":
    main()
