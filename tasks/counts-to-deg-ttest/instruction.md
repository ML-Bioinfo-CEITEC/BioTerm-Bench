Inputs:

- `/app/data/counts.tsv` — TAB-separated gene × sample count matrix.
  Header row: `gene_id<TAB>ctrl_1<TAB>ctrl_2<TAB>ctrl_3<TAB>trt_1<TAB>trt_2<TAB>trt_3`.
  One row per gene.
- `/app/data/samples.tsv` — TAB-separated sample metadata with
  columns `sample`, `group` (values `ctrl` or `trt`).

Compute a simple differential-expression table:

1. Convert counts to **CPM** per sample: `cpm[g, s] = counts[g, s] /
   sum_g counts[g, s] * 1e6`.
2. For every gene, run a **Welch's two-sample t-test**
   (`scipy.stats.ttest_ind(..., equal_var=False)`) comparing `ctrl`
   CPM values (3 samples) with `trt` CPM values (3 samples). Treat a
   NaN t-statistic as 0.0 and a NaN p-value as 1.0 (happens for
   all-zero rows).
3. Rank genes by `|t_stat|` descending; break ties by `gene_id`
   ASCII ascending. Keep the top **20** genes.

Write `/app/output/top_deg.tsv` with this exact header line followed
by 20 data rows:

    gene_id    t_stat    p_value    mean_cpm_ctrl    mean_cpm_trt

Formatting:

- `t_stat` — 4 decimal places, e.g. `-12.3456`.
- `p_value` — scientific notation with 6 decimals after the point,
  lowercase `e`, no leading zero padding of the exponent, e.g.
  `1.234567e-08`.
- `mean_cpm_ctrl`, `mean_cpm_trt` — 4 decimal places.

Grading is numeric: the 20 `gene_id`s must match gold in that order,
and each numeric column must agree within `1e-4` (relative or
absolute tolerance of `1e-4` on `p_value`, using Python's `math.isclose`
with `rel_tol=1e-4, abs_tol=1e-9`).
