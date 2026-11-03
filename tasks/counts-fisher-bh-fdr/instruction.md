`/app/data/counts.tsv` gives, for each of 400 genes, four counts:
`alt_case`, `ref_case`, `alt_control`, `ref_control`.

Test each gene for an association between allele and group, then control
the false discovery rate.

For each gene run a **two-sided Fisher exact test** on the 2x2 table whose
first row is `[alt_case, ref_case]` and whose second row is
`[alt_control, ref_control]`.

Adjust the 400 p-values with the **Benjamini-Hochberg** procedure: rank
them ascending, set `q = p * 400 / rank`, then enforce monotonicity by
walking from the largest rank down and replacing each `q` with the smallest
`q` seen so far at or above it. Keep only genes with `q < 0.05`.

Write `/app/output/significant.tsv` with header

`gene	alt_case	ref_case	alt_control	ref_control	p_value	q_value`

one row per significant gene, sorted by ascending `p_value` and then by
gene name, echoing the four input counts and giving `p_value` and
`q_value` in scientific notation with six decimals, as `1.234567e-05`.
