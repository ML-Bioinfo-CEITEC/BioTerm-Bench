The files `/app/data/counts.tsv`, `/app/data/samples.tsv`, and
`/app/data/annotation.tsv` define a bulk RNA-seq differential
expression problem.

1. Use `counts.tsv` as the raw gene-by-sample count matrix.
2. Use the design formula `~ batch + condition`.
3. Compare `treated` versus `control`.
4. Before fitting, keep only genes with counts of at least 10 in at
   least 3 samples.
5. After fitting, inner-join `annotation.tsv` on `gene_id`, keep only
   `protein_coding` genes, and drop rows with missing adjusted p-value.
6. Rank by `padj` ascending, then by `abs(log2FoldChange)` descending,
   then by `gene_id` ASCII ascending. Keep the top 25 rows.

Write `/app/output/de_hits.tsv` with header:

`gene_id<TAB>gene_name<TAB>baseMean<TAB>log2FoldChange<TAB>padj`

Format the three numeric columns with 6 decimal places and end with a
trailing newline.
