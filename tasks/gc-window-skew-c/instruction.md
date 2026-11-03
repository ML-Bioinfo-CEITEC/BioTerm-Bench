`/app/data/case.json` contains the complete input for this candidate and an
`operation` field equal to `gc_windows`. Compute filtered sliding-window GC fraction and GC skew. Windows are 1-based inclusive in the output; only complete windows are considered.

Parameters for this fixture: window=61, step=4, min_gc=0.54, input_schema=sequences: objects with id and sequence.
Do not assume records are pre-sorted unless the requested output order says so.

Write `/app/output/result.tsv`. The exact required header is documented in
`/app/data/output_header.txt`. Emit rows in this order: input sequence order, then increasing window start.
Numeric output may contain additional precision.
