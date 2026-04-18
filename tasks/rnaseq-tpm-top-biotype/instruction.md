Inputs:

- `/app/data/counts.tsv` — TAB-separated gene × sample integer count
  matrix. Header: `gene_id<TAB>s1<TAB>...<TAB>s6`.
- `/app/data/gene_lengths.tsv` — two columns, `gene_id<TAB>length_bp`.
- `/app/data/annotation.tsv` — three columns: `gene_id<TAB>gene_name<TAB>biotype`.

1. Inner-join the three tables on `gene_id`. Drop any gene that is
   missing from any of the three.
2. Keep only genes with `biotype == "protein_coding"`.
3. Compute **TPM** per sample using `gene_lengths.length_bp`:
   `rate[g, s] = counts[g, s] / length_bp[g]`;
   `tpm[g, s] = 1e6 * rate[g, s] / sum_g(rate[g, s])`.
4. For each kept gene, compute `max_tpm = max(tpm[g, :])` across all
   samples.
5. Rank genes by `max_tpm` descending; break ties by `gene_id` ASCII
   ascending. Keep the **top 30**.

Write `/app/output/top_biotype.tsv` with this header and 30 rows:

    gene_id    gene_name    max_tpm

`max_tpm` formatted with 4 decimals. TAB-separated, trailing newline.

Grading: exact match on the 30 `(gene_id, gene_name)` pairs in order,
and `|actual - gold| <= 1e-3` on `max_tpm`.
