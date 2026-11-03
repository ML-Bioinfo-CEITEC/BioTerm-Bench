`/app/data/pairs.bam` (indexed) holds paired-end alignments over two contigs.

Classify read pairs by relative orientation and summarise each class.

Count each pair once, from its **read1** record only, and only if that
record is: paired (`0x1`), proper pair (`0x2`), read1 (`0x40`), not
secondary (`0x100`), not supplementary (`0x800`), not duplicate (`0x400`),
itself mapped (not `0x4`), mate mapped (not `0x8`), and mate on the same
reference.

Orientation comes from the two strand flags:

- `TANDEM` if read and mate are on the same strand;
- otherwise find the leftmost read by position (`POS` vs `PNEXT`; on a tie
  treat read1 as leftmost). It is `FR` if that leftmost read is forward,
  `RF` if it is reverse.

Write `/app/output/pair_orientation.tsv` with header

`orientation	n_pairs	median_abs_tlen`

and exactly three rows in the order `FR`, `RF`, `TANDEM`.
`median_abs_tlen` is the median of `abs(TLEN)` over the counted read1
records to one decimal, using the mean of the two middle values when the
count is even, and `0.0` for an empty class.
