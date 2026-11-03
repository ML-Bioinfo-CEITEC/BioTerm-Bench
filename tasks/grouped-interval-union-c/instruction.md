`/app/data/case.json` contains the complete input for this candidate and an
`operation` field equal to `interval_union`. Merge zero-based half-open intervals independently by group. Merge overlapping intervals and intervals separated by no more than max_gap bases; compute raw and union lengths.

Parameters for this fixture: max_gap=2, input_schema=intervals: [group, start_0based, end_0based_exclusive].
Do not assume records are pre-sorted unless the requested output order says so.

Write `/app/output/result.tsv`. The exact required header is documented in
`/app/data/output_header.txt`. Emit rows in this order: group alphabetically.
Numeric output may contain additional precision.
