#!/usr/bin/env python3
"""Generate a counts matrix + gold DESeq2-style size factors.

Writes:
  /out/data/counts.tsv
  /out/gold/size_factors.tsv
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

SEED = 20260418
N_GENES = 400
SAMPLES = ["s1", "s2", "s3", "s4", "s5", "s6"]

DATA = Path("/out/data/counts.tsv")
GOLD = Path("/out/gold/size_factors.tsv")


def main() -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(SEED)
    # Sample-specific scale factors
    true_sf = np.array([0.80, 1.00, 1.20, 0.90, 1.10, 0.95])
    # Gene baseline expression
    base = np.exp(rng.normal(loc=3.0, scale=1.5, size=N_GENES))
    base = np.clip(base, 2.0, 2000.0)

    counts = np.zeros((N_GENES, len(SAMPLES)), dtype=np.int64)
    for g in range(N_GENES):
        for s in range(len(SAMPLES)):
            mu = base[g] * true_sf[s]
            counts[g, s] = max(0, int(rng.poisson(mu)))

    gene_ids = [f"GENE{i:04d}" for i in range(1, N_GENES + 1)]

    with DATA.open("w") as fh:
        fh.write("gene_id\t" + "\t".join(SAMPLES) + "\n")
        for g, gid in enumerate(gene_ids):
            fh.write(gid + "\t" + "\t".join(str(c) for c in counts[g]) + "\n")

    # Canonical DESeq2 size-factor recipe:
    #   - log-geometric mean across samples (rows with any 0 are dropped)
    #   - per-sample size factor = median of (count / geomean) over kept rows
    log_c = np.log(counts.astype(float))
    keep = np.all(counts > 0, axis=1)
    if not keep.any():
        raise RuntimeError("no genes with counts>0 in every sample")
    logmean = log_c[keep].mean(axis=1)         # per-gene
    ratios = log_c[keep] - logmean[:, None]     # per (gene, sample), in log
    sf_log = np.median(ratios, axis=0)         # per-sample median of log ratios
    sf = np.exp(sf_log)

    with GOLD.open("w") as fh:
        fh.write("sample\tsize_factor\n")
        for s, v in zip(SAMPLES, sf):
            fh.write(f"{s}\t{v:.6f}\n")
    print(f"wrote {DATA} and gold size factors: "
          + ", ".join(f"{s}={v:.4f}" for s, v in zip(SAMPLES, sf)))


if __name__ == "__main__":
    main()
