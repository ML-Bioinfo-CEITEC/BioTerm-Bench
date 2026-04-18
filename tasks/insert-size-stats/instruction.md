The file `/app/data/reads.bam` is a coordinate-sorted BAM of
paired-end alignments with realistic TLEN values.

Produce one output file:

- `/app/output/insert.json` — a JSON object with exactly these two
  keys and no others:

        {
          "mean_insert":  <number>,
          "stdev_insert": <number>
        }

Semantics:

- `mean_insert` is the arithmetic mean of the insert size (in bases)
  as reported by `samtools stats` under the `SN` line
  `insert size average`. It is a floating-point number.
- `stdev_insert` is the `insert size standard deviation` reported by
  the same `samtools stats` `SN` section. It is a floating-point
  number.

If you compute the statistics yourself instead of reading them from
`samtools stats`, match its convention: only primary, properly
paired, non-supplementary, non-secondary alignments contribute, and
insert size is the absolute value of `TLEN` taken from the first
mate of each pair.

Emit the JSON with sorted keys and 2-space indentation.
