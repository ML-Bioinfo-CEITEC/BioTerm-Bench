The file `/app/data/reads.fastq.gz` is a single-end gzipped FASTQ.

Run FastQC on this file and extract five values from the resulting
`fastqc_data.txt` report. Write them to:

- `/app/output/qc_summary.json` — JSON object with exactly these keys:

      {
        "total_sequences":      <int>,   // "Total Sequences"
        "sequence_length_min":  <int>,   // left of the dash in
                                         //   "Sequence length"
                                         // (or the single value if no dash)
        "sequence_length_max":  <int>,   // right of the dash (or same as
                                         //   min for a single value)
        "gc_content":           <int>,   // "%GC" integer
        "per_base_q20_frac":    <float>  // fraction of per-base positions
                                         //   in the "Per base sequence
                                         //   quality" module whose Mean
                                         //   is >= 20.0; range [0, 1].
      }

Integer counts must be exact. `per_base_q20_frac` is compared with a 5%
relative tolerance.
