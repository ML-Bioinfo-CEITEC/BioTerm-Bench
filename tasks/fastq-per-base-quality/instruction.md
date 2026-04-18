The file `/app/data/reads.fastq.gz` is a gzipped single-end FASTQ in
Phred+33 encoding (Phred quality of character `q` is `ord(q) - 33`).
Reads have varying lengths.

For every **0-based position** `i` at which at least one read has a
base, compute three statistics over the quality scores of all reads
that cover position `i`:

- `mean_q` — arithmetic mean
- `median_q` — 50th percentile via `numpy.percentile` defaults
  (linear interpolation)
- `n` — the number of reads covering that position

Write `/app/output/per_base_quality.tsv` with this exact header line
followed by one row per covered position, in ascending `pos` order:

    pos    n    mean_q    median_q

Format:

- `pos` and `n` — plain integers.
- `mean_q` — 4 decimals, e.g. `32.1234`.
- `median_q` — 4 decimals.
- TAB-separated, one trailing newline after the last row.

Grading: exact match on `pos` and `n`; `|actual - gold| <= 1e-3` on
the two floats.
