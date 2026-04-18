The file `/app/data/reads.bam` is a coordinate-sorted, paired-end
BAM. Every record is primary and mapped (no secondary / supplementary
alignments). A subset of reads carry soft-clip operations (`S`) at
the 5' end, the 3' end, or both.

Compute per-read soft-clip statistics and emit:

- `/app/output/stats.json` with exactly these keys:

        {
          "n_primary_mapped":    <int>,
          "n_with_any_clip":     <int>,
          "mean_total_clip":     <float, 4 decimals>,
          "p90_total_clip":      <float, 4 decimals>
        }

Semantics (evaluate each CIGAR as written):

- `left_clip` = length of the leading `S` run (0 otherwise).
- `right_clip` = length of the trailing `S` run (0 otherwise).
- `total_clip = left_clip + right_clip`.
- `n_primary_mapped` is the number of primary mapped reads.
- `n_with_any_clip` counts reads where `total_clip > 0`.
- `mean_total_clip` is the mean of `total_clip` over **all**
  `n_primary_mapped` reads (including zeros).
- `p90_total_clip` is the 90th percentile of `total_clip` **among
  clipped reads only**, computed with `numpy.percentile` defaults
  (linear interpolation).

Emit JSON with sorted keys and 2-space indentation. Floats must be
rounded to 4 decimals; grading tolerance is `1e-3` on floats and
exact on the two integers.
