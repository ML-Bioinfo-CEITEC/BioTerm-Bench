#!/usr/bin/env python3
"""Generate a synthetic count matrix + DESeq2 gold contrast table.

Writes:
  /out/data/counts.tsv
  /out/data/samples.tsv
  /out/data/annotation.tsv
  /out/gold/de_hits.tsv
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

OUT_DATA = Path("/out/data")
OUT_GOLD = Path("/out/gold")
SEED = 20260812
N_GENES = 240
TOP_N = 25

SAMPLES = [
    ("C1", "control", "batch1"),
    ("C2", "control", "batch1"),
    ("C3", "control", "batch2"),
    ("C4", "control", "batch2"),
    ("T1", "treated", "batch1"),
    ("T2", "treated", "batch1"),
    ("T3", "treated", "batch2"),
    ("T4", "treated", "batch2"),
]


def _run_deseq2(counts_path: Path, samples_path: Path, ann_path: Path, out_path: Path) -> None:
    script = f"""
    suppressPackageStartupMessages(library(DESeq2))

    counts <- read.delim("{counts_path}", check.names = FALSE)
    samples <- read.delim("{samples_path}")
    ann <- read.delim("{ann_path}")

    mat <- as.matrix(counts[, -1, drop = FALSE])
    rownames(mat) <- counts$gene_id
    storage.mode(mat) <- "integer"
    samples <- samples[match(colnames(mat), samples$sample_id), , drop = FALSE]
    samples$condition <- factor(samples$condition, levels = c("control", "treated"))
    samples$batch <- factor(samples$batch)

    keep <- rowSums(mat >= 10) >= 3
    dds <- DESeqDataSetFromMatrix(countData = mat[keep, , drop = FALSE], colData = samples, design = ~ batch + condition)
    dds <- DESeq(dds, quiet = TRUE)
    res <- as.data.frame(results(dds, contrast = c("condition", "treated", "control"), alpha = 0.05))
    res$gene_id <- rownames(res)

    joined <- merge(res, ann, by = "gene_id", all.x = TRUE, sort = FALSE)
    joined <- joined[joined$biotype == "protein_coding" & !is.na(joined$padj),
                     c("gene_id", "gene_name", "baseMean", "log2FoldChange", "padj")]
    ord <- order(joined$padj, -abs(joined$log2FoldChange), joined$gene_id)
    joined <- joined[ord, , drop = FALSE]
    top <- head(joined, {TOP_N})
    top$baseMean <- sprintf("%.6f", top$baseMean)
    top$log2FoldChange <- sprintf("%.6f", top$log2FoldChange)
    top$padj <- sprintf("%.6f", top$padj)
    write.table(top, file = "{out_path}", sep = "\\t", quote = FALSE, row.names = FALSE)
    """
    subprocess.run(["Rscript", "-"], input=script, text=True, check=True)


def main() -> None:
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    OUT_GOLD.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(SEED)
    gene_ids = [f"ENSGDE{i:05d}" for i in range(1, N_GENES + 1)]
    gene_names = [f"GeneDE{i:03d}" for i in range(1, N_GENES + 1)]

    biotypes = np.array(["lncRNA"] * N_GENES, dtype=object)
    biotypes[:170] = "protein_coding"
    rng.shuffle(biotypes)

    base_means = rng.lognormal(mean=4.2, sigma=0.65, size=N_GENES)
    dispersions = rng.uniform(0.08, 0.22, size=N_GENES)
    condition_lfc = np.zeros(N_GENES)
    batch_lfc = np.zeros(N_GENES)

    pc_idx = np.flatnonzero(biotypes == "protein_coding")
    up_idx = pc_idx[:18]
    down_idx = pc_idx[18:36]
    mild_idx = pc_idx[36:48]
    batch_idx = np.arange(48, 78)

    condition_lfc[up_idx] = rng.uniform(1.6, 2.5, size=len(up_idx))
    condition_lfc[down_idx] = -rng.uniform(1.4, 2.2, size=len(down_idx))
    condition_lfc[mild_idx] = rng.uniform(0.7, 1.1, size=len(mild_idx))
    batch_lfc[batch_idx] = rng.uniform(0.6, 1.1, size=len(batch_idx))

    counts = np.zeros((N_GENES, len(SAMPLES)), dtype=int)
    for s_idx, (_sample_id, condition, batch) in enumerate(SAMPLES):
        cond_mult = np.exp2(condition_lfc) if condition == "treated" else np.ones(N_GENES)
        batch_mult = np.exp2(batch_lfc) if batch == "batch2" else np.ones(N_GENES)
        mu = np.clip(base_means * cond_mult * batch_mult, 1.0, None)
        for g_idx in range(N_GENES):
            alpha = dispersions[g_idx]
            n = 1.0 / alpha
            p = n / (n + mu[g_idx])
            counts[g_idx, s_idx] = int(rng.negative_binomial(n, p))

    for g_idx in up_idx[:10]:
        counts[g_idx, 4:] += rng.integers(25, 60, size=4)
    for g_idx in down_idx[:10]:
        counts[g_idx, :4] += rng.integers(18, 45, size=4)

    counts_df = pd.DataFrame(counts, columns=[sample_id for sample_id, _, _ in SAMPLES])
    counts_df.insert(0, "gene_id", gene_ids)
    counts_df.to_csv(OUT_DATA / "counts.tsv", sep="\t", index=False)

    samples_df = pd.DataFrame(SAMPLES, columns=["sample_id", "condition", "batch"])
    samples_df.to_csv(OUT_DATA / "samples.tsv", sep="\t", index=False)

    ann_df = pd.DataFrame(
        {"gene_id": gene_ids, "gene_name": gene_names, "biotype": biotypes}
    )
    ann_df.to_csv(OUT_DATA / "annotation.tsv", sep="\t", index=False)

    _run_deseq2(
        OUT_DATA / "counts.tsv",
        OUT_DATA / "samples.tsv",
        OUT_DATA / "annotation.tsv",
        OUT_GOLD / "de_hits.tsv",
    )
    print(
        "wrote counts.tsv, samples.tsv, annotation.tsv and DESeq2 gold "
        f"(top {TOP_N})"
    )


if __name__ == "__main__":
    main()
