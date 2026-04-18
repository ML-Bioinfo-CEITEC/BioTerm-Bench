The file `/app/data/intervals.bed` is a 3-column BED file (chrom,
start, end) that is **not sorted**. Some intervals on the same chrom
overlap or are adjacent.

Produce one output file:

- `/app/output/merged.bed` — the same intervals after merging any
  pair whose gap on the same chromosome is at most **50** base pairs.
  Two intervals are merged if `next.start - prev.end <= 50` (so
  overlapping and book-ending intervals also merge). The merged
  interval spans from the minimum `start` to the maximum `end` of the
  group.

Format of the output file:

- Plain tab-separated BED3 (chrom, start, end) — no header, no
  extra columns, no comment lines.
- Sorted by `chrom` lexicographically (ASCII), then by `start`
  numerically ascending.
- Coordinates are 0-based, half-open (the standard BED convention).
- No duplicates and no empty lines.
