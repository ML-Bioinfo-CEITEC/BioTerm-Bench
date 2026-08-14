#!/usr/bin/env python3
"""Generate a synthetic RNA-seq counts matrix + gene lengths +
annotation, plus the gold top-30 protein-coding genes by max TPM.

Writes:
  /out/data/counts.tsv
  /out/data/gene_lengths.tsv
  /out/data/annotation.tsv
  /out/gold/top_biotype.tsv
"""
from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20260418
OUT_DATA = Path("/out/data")
OUT_GOLD = Path("/out/gold")

N_GENES = 400
SAMPLES = [f"s{i}" for i in range(1, 7)]


def main() -> None:
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    OUT_GOLD.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    np_rng = np.random.default_rng(SEED)

    gene_ids = [f"ENSG{100000 + i:06d}" for i in range(N_GENES)]
    gene_names = [f"GeneN{i:04d}" for i in range(N_GENES)]
    biotypes_pool = ["protein_coding", "lncRNA", "miRNA", "processed_pseudogene", "snRNA"]
    weights = [0.5, 0.2, 0.1, 0.15, 0.05]
    biotypes = rng.choices(biotypes_pool, weights=weights, k=N_GENES)

    lengths = np_rng.integers(500, 15_000, size=N_GENES)
    # counts ~ Negative binomial-ish
    raw = np_rng.negative_binomial(5, 0.2, size=(N_GENES, len(SAMPLES)))

    counts_df = pd.DataFrame(raw, index=gene_ids, columns=SAMPLES)
    counts_df.index.name = "gene_id"
    counts_df.to_csv(OUT_DATA / "counts.tsv", sep="\t")

    lengths_df = pd.DataFrame({"gene_id": gene_ids, "length_bp": lengths})
    lengths_df.to_csv(OUT_DATA / "gene_lengths.tsv", sep="\t", index=False)

    ann_df = pd.DataFrame(
        {"gene_id": gene_ids, "gene_name": gene_names, "biotype": biotypes}
    )

    # DROP some gene_ids from each table so grader must really inner-join
    drop_from_counts = rng.sample(gene_ids, 20)
    drop_from_lengths = rng.sample(gene_ids, 15)
    drop_from_annot = rng.sample(gene_ids, 25)
    counts_df = counts_df.drop(index=[g for g in drop_from_counts if g in counts_df.index])
    lengths_df = lengths_df[~lengths_df["gene_id"].isin(drop_from_lengths)]
    ann_df = ann_df[~ann_df["gene_id"].isin(drop_from_annot)]

    # Re-write after drops
    counts_df.to_csv(OUT_DATA / "counts.tsv", sep="\t")
    lengths_df.to_csv(OUT_DATA / "gene_lengths.tsv", sep="\t", index=False)
    ann_df.to_csv(OUT_DATA / "annotation.tsv", sep="\t", index=False)

    # Gold
    joined = counts_df.reset_index().merge(lengths_df, on="gene_id", how="inner").merge(
        ann_df, on="gene_id", how="inner"
    )
    pc = joined[joined["biotype"] == "protein_coding"].copy()
    rate = pc[SAMPLES].div(pc["length_bp"].values, axis=0)
    tpm = rate.div(rate.sum(axis=0), axis=1) * 1e6
    pc["max_tpm"] = tpm.max(axis=1).values
    pc = pc.sort_values(by=["max_tpm", "gene_id"], ascending=[False, True])
    top = pc.head(30)[["gene_id", "gene_name", "max_tpm"]].copy()
    top["max_tpm"] = top["max_tpm"].map(lambda x: f"{x:.4f}")
    gold_path = OUT_GOLD / "top_biotype.tsv"
    with gold_path.open("w") as fh:
        fh.write("gene_id\tgene_name\tmax_tpm\n")
        for _, r in top.iterrows():
            fh.write(f"{r['gene_id']}\t{r['gene_name']}\t{r['max_tpm']}\n")

    print(f"wrote data and {gold_path}; joined {len(joined)} genes, "
          f"{(pc.shape[0])} protein_coding, top=30")


if __name__ == "__main__":
    main()
