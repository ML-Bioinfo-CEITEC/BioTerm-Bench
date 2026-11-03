`/app/data/case.json` contains the complete input for this candidate and an
`operation` field equal to `deseq_size_factors`. For each gene positive in every sample, take the geometric mean across samples and form count/geometric-mean ratios. Each sample's raw size factor is the ordinary median of its ratios (average the middle two when even). Divide all raw factors by their geometric mean. Normalize every gene, including zero-containing genes, as count/size-factor. genes_used is the number of positive-in-every-sample genes; normalized_sum and normalized_median summarize all normalized genes.

Parameters for this fixture: input_schema=genes: [gene_id, count_per_sample]; count order matches samples.
Do not assume records are pre-sorted unless the requested output order says so.

Write `/app/output/result.tsv`. The exact required header is documented in
`/app/data/output_header.txt`. Emit rows in this order: input sample order.
Numeric output may contain additional precision.
