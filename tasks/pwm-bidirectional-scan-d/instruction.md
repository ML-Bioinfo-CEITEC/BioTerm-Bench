`/app/data/case.json` contains the complete input for this candidate and an
`operation` field equal to `motif_pwm`. Scan every sequence on both strands with the supplied position-weight matrix. Use log2(P(base)/0.25), report hits at or above the threshold, and express reverse hits at their forward-reference start.

Parameters for this fixture: threshold=10.799999999999999, input_schema=pwm: list of per-position base-probability objects; sequences: objects with id and sequence.
Do not assume records are pre-sorted unless the requested output order says so.

Write `/app/output/result.tsv`. The exact required header is documented in
`/app/data/output_header.txt`. Emit rows in this order: sequence ID, start, then strand, all ascending.
Numeric output may contain additional precision.
