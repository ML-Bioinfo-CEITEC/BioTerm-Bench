`/app/data/case.json` contains the complete input for this candidate and an
`operation` field equal to `canonical_kmers`. Count canonical DNA k-mers across all sequences. A canonical k-mer is the lexicographically smaller of the observed k-mer and its reverse complement; discard windows containing non-ACGT symbols.

Parameters for this fixture: k=11, minimum_count=2, input_schema=sequences: objects with id and sequence.
Do not assume records are pre-sorted unless the requested output order says so.

Write `/app/output/result.tsv`. The exact required header is documented in
`/app/data/output_header.txt`. Emit rows in this order: decreasing count, then canonical k-mer alphabetically.
Numeric output may contain additional precision.
