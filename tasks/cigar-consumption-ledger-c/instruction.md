`/app/data/case.json` contains the complete input for this candidate and an
`operation` field equal to `cigar_accounting`. Parse each SAM CIGAR and separately total reference span, query consumption, aligned bases, insertions, deletions, reference skips, and soft plus hard clipping.

Parameters for this fixture: input_schema=records: [read_id, cigar].
Do not assume records are pre-sorted unless the requested output order says so.

Write `/app/output/result.tsv`. The exact required header is documented in
`/app/data/output_header.txt`. Emit rows in this order: input record order.
Numeric output may contain additional precision.
