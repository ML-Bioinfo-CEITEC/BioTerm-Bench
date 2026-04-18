The file `/app/data/reads.fastq.gz` is a gzipped single-end FASTQ in
Phred+33 encoding (quality char `q` has Phred value `ord(q) - 33`).

Quality-trim each read from the **3' end** at threshold Q20:

- Starting at the last base, walk leftwards while Phred `< 20`.
- Stop at the first base with Phred `>= 20`. That base is kept.
- If every base is below threshold, the read becomes length 0 and
  is dropped.

Compute summary statistics and write them to
`/app/output/stats.json` with exactly these keys:

    {
      "n_in":         <int>,          # number of reads read
      "n_out":        <int>,          # reads surviving (length > 0)
      "bases_in":     <int>,          # total input bases
      "bases_out":    <int>,          # total bases in surviving reads
      "mean_len_in":  <float, 4 dp>,  # bases_in / n_in
      "mean_len_out": <float, 4 dp>   # bases_out / n_out; 0.0 if n_out == 0
    }

Emit JSON with sorted keys and 2-space indentation. Grading is
exact on the four integers and `|actual - gold| <= 1e-3` on the two
floats. You do not need to emit a trimmed FASTQ, only `stats.json`.
