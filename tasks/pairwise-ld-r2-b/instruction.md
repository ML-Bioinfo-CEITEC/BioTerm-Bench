`/app/data/case.json` contains the complete input for this candidate and an
`operation` field equal to `ld_r2`. For every variant pair, use samples called at both sites and compute squared Pearson correlation of diploid dosages. Keep pairs meeting both the sample-count and r-squared thresholds.

Parameters for this fixture: min_pairs=12, min_r2=0.22, input_schema=variants: [variant_id, dosage_per_sample]; -1 is missing.
Do not assume records are pre-sorted unless the requested output order says so.

Write `/app/output/result.tsv`. The exact required header is documented in
`/app/data/output_header.txt`. Emit rows in this order: decreasing r-squared, then variant A and variant B alphabetically.
Numeric output may contain additional precision.
