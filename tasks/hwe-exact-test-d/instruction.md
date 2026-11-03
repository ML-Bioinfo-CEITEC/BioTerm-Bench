`/app/data/case.json` contains the complete input for this candidate and an
`operation` field equal to `hwe_exact`. Compute the two-sided exact Hardy-Weinberg p-value conditional on minor-allele count, summing genotype configurations whose probability is no greater than the observed configuration. Encode fails_hwe as 1 or 0.

Parameters for this fixture: alpha=0.05, input_schema=counts: [variant_id, hom_ref_count, hom_alt_count, heterozygous_count].
Do not assume records are pre-sorted unless the requested output order says so.

Write `/app/output/result.tsv`. The exact required header is documented in
`/app/data/output_header.txt`. Emit rows in this order: input variant order.
Numeric output may contain additional precision.
