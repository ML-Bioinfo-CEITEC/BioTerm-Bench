`/app/data/counts.tsv` is a gene-by-sample RNA-seq count matrix: 4000 genes
down the rows, 12 samples across the columns.

Produce **three** files in `/app/output`. All three are graded.

`sample_qc.tsv`, header `sample	library_size	n_detected	status`, one row
per sample in input column order. `library_size` is that sample's total
count, `n_detected` its number of genes with a count above zero. A sample's
`status` is `fail` when its library size is below 30% of the median library
size across all 12 samples, or when fewer than 1200 genes are detected;
otherwise `pass`.

`gene_filter.tsv`, header `gene	n_samples_expressed	mean_cpm`, computed
over the passing samples only. CPM is a gene's count divided by that
sample's library size, times one million. Keep a gene when at least three
passing samples have CPM of 1.0 or more. `mean_cpm` is the gene's mean CPM
across all passing samples, to four decimals. Keep input gene order.

`summary.tsv`, header `metric	value`, with rows `n_samples_total`,
`n_samples_passing`, `n_genes_total`, `n_genes_retained` and
`median_library_size` in that order, the last to one decimal.
