`/app/data/case.json` contains the complete input for this candidate and an
`operation` field equal to `genotype_qc`. From diploid alternate-allele dosages (0, 1, 2; -1 missing), compute per-sample call rate, heterozygosity among called genotypes, and total alternate alleles.

Parameters for this fixture: input_schema=variants: [variant_id, dosage_per_sample]; dosage order matches samples.
Do not assume records are pre-sorted unless the requested output order says so.

Write `/app/output/result.tsv`. The exact required header is documented in
`/app/data/output_header.txt`. Emit rows in this order: input sample order.
Numeric output may contain additional precision.
