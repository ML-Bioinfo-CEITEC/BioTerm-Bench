The file `/app/data/reads.bam` is a coordinate-sorted, paired-end
BAM that has already been run through `samtools fixmate -m` (so MC
and MS tags are present). It contains some read pairs that start at
the same 5' positions and should therefore be flagged as PCR
duplicates.

Produce one output file:

- `/app/output/counts.json` — a JSON object with exactly these two
  keys:

        {
          "duplicates":    <int>,
          "primary_total": <int>
        }

Semantics:

- `duplicates` is the number of **primary** alignment records that
  end up with the duplicate flag set (SAM flag bit `0x400`) after
  running the standard `samtools markdup` algorithm on
  `/app/data/reads.bam`. It is the flagstat "duplicates" count on
  the marked output.
- `primary_total` is the number of **primary** alignment records
  in the marked output (flagstat "primary" count). Supplementary
  and secondary alignments are excluded.

Emit the JSON with sorted keys and 2-space indentation. A trailing
newline is fine.
