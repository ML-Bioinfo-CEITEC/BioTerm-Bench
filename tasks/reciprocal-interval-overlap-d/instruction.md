`/app/data/case.json` contains the complete input for this candidate and an
`operation` field equal to `reciprocal_overlap`. Report interval pairs on the same contig whose half-open overlap covers at least the required fraction of each interval. Boundary touching alone has zero overlap.

Parameters for this fixture: fraction=0.7, input_schema=a and b: [interval_id, contig, start_0based, end_0based_exclusive].
Do not assume records are pre-sorted unless the requested output order says so.

Write `/app/output/result.tsv`. The exact required header is documented in
`/app/data/output_header.txt`. Emit rows in this order: A interval ID, then B interval ID, alphabetically.
Numeric output may contain additional precision.
