`/app/data/case.json` contains the complete input for this candidate and an
`operation` field equal to `pileup_consensus`. Call the most frequent base at each pileup site only when minimum depth and top-base fraction are met; otherwise call N. Break count ties alphabetically. Encode differs_from_reference as 1 only for a called A/C/G/T base unequal to the reference; an N call is 0.

Parameters for this fixture: min_depth=20, min_fraction=0.55, input_schema=sites: [contig, position_1based, reference_base, {base: count}].
Do not assume records are pre-sorted unless the requested output order says so.

Write `/app/output/result.tsv`. The exact required header is documented in
`/app/data/output_header.txt`. Emit rows in this order: input site order.
Numeric output may contain additional precision.
