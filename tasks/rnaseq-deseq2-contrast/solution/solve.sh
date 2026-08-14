#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

Rscript - <<'RS'
suppressPackageStartupMessages(library(DESeq2))

counts <- read.delim("/app/data/counts.tsv", check.names = FALSE)
samples <- read.delim("/app/data/samples.tsv")
ann <- read.delim("/app/data/annotation.tsv")

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
top <- head(joined[ord, , drop = FALSE], 25)
top$baseMean <- sprintf("%.6f", top$baseMean)
top$log2FoldChange <- sprintf("%.6f", top$log2FoldChange)
top$padj <- sprintf("%.6f", top$padj)
write.table(top, file = "/app/output/de_hits.tsv", sep = "\t", quote = FALSE, row.names = FALSE)
RS
