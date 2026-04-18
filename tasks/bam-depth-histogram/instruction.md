The file `/app/data/reads.bam` is a coordinate-sorted, indexed BAM of
reads aligned to the SARS-CoV-2 reference (contig name
`NC_045512.2`).

Compute per-base coverage statistics over the full reference and
write them as JSON. Use `samtools depth -a` (the `-a` flag makes
zero-coverage positions explicit) as the source of truth; compute the
stats over every position in the reference, including positions with
depth 0.

Produce one output file:

- `/app/output/coverage.json` — a UTF-8 JSON object with exactly
  these keys and value types:

      {
        "ref_length":       <int>,    // total number of positions
                                       //   emitted by `samtools depth -a`
        "mean_depth":       <float>,  // mean depth across those positions
        "median_depth":     <int>,    // median depth (pick the lower of
                                       //   the two middle values if length
                                       //   is even)
        "fraction_covered": <float>,  // fraction of positions whose depth
                                       //   is >= 1 ; range [0, 1]
        "max_depth":        <int>     // maximum depth observed
      }

`ref_length`, `median_depth`, and `max_depth` must match exactly.
`mean_depth` and `fraction_covered` are compared with 1% relative
tolerance.
