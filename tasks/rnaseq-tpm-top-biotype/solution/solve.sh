#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output

python3 - <<'PY'
import pandas as pd

COUNTS = "/app/data/counts.tsv"
LEN = "/app/data/gene_lengths.tsv"
ANN = "/app/data/annotation.tsv"
OUT = "/app/output/top_biotype.tsv"

counts = pd.read_csv(COUNTS, sep="\t")
lengths = pd.read_csv(LEN, sep="\t")
annot = pd.read_csv(ANN, sep="\t")

joined = counts.merge(lengths, on="gene_id", how="inner").merge(
    annot, on="gene_id", how="inner"
)
pc = joined[joined["biotype"] == "protein_coding"].copy()

samples = [c for c in counts.columns if c != "gene_id"]
rate = pc[samples].div(pc["length_bp"].values, axis=0)
tpm = rate.div(rate.sum(axis=0), axis=1) * 1e6
pc["max_tpm"] = tpm.max(axis=1).values

pc = pc.sort_values(by=["max_tpm", "gene_id"], ascending=[False, True])
top = pc.head(30)[["gene_id", "gene_name", "max_tpm"]].copy()
top["max_tpm"] = top["max_tpm"].map(lambda x: f"{x:.4f}")

with open(OUT, "w") as fh:
    fh.write("gene_id\tgene_name\tmax_tpm\n")
    for _, r in top.iterrows():
        fh.write(f"{r['gene_id']}\t{r['gene_name']}\t{r['max_tpm']}\n")
PY
