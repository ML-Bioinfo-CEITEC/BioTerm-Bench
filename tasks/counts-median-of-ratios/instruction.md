Input `/app/data/counts.tsv` is a TAB-separated gene × sample count
matrix. Header row: `gene_id<TAB>s1<TAB>s2<TAB>...<TAB>s6`. One row
per gene, integer counts.

Compute **DESeq2-style size factors** (the "median-of-ratios"
estimator):

1. Drop any gene that has a zero count in **any** sample.
2. On the remaining genes, compute the **geometric mean** across
   samples for each gene:
   `geomean[g] = exp(mean_s(log(count[g, s])))`.
3. For every (gene, sample) on the kept genes, form the ratio
   `r[g, s] = count[g, s] / geomean[g]`.
4. The size factor for sample `s` is the **median** of `r[:, s]`
   across the kept genes.

Write `/app/output/size_factors.tsv` with this exact header and one
row per sample in the input column order:

    sample    size_factor

`size_factor` formatted with 6 decimal places, e.g. `1.012345`.

Grading is numeric: the `sample` column must match exactly in the
input column order, and each `size_factor` must be within `1e-4`
(absolute tolerance) of gold. If zero genes survive step (1), the
task is infeasible — do not try to handle that; the provided data
has plenty of non-zero rows.
