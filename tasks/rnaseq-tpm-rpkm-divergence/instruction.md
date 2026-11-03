`/app/data/counts.tsv` gives 800 genes with their length in bases and raw
counts in six samples.

Compute TPM and RPKM for every gene in every sample and find where the two
measures disagree most.

The two differ only in the order of the two normalisations, and that order
matters.

- **RPKM**: divide a gene's count by its length in kilobases, then by the
  sample's total count in millions.
- **TPM**: first divide every gene's count by its length in kilobases to
  get rates, then divide each rate by the **sum of that sample's rates**
  and multiply by one million.

For each gene take its mean TPM and mean RPKM across the six samples. Rank
genes by descending mean TPM, and separately by descending mean RPKM, in
both cases breaking ties by gene name ascending, with rank 1 the highest.
`rank_shift` is the absolute difference between a gene's two ranks.

Write `/app/output/rank_divergence.tsv` with header

`gene	mean_tpm	mean_rpkm	rank_tpm	rank_rpkm	rank_shift`

for the 40 genes with the largest `rank_shift`, sorted by descending
`rank_shift` then by gene name, with the two means to four decimals.
