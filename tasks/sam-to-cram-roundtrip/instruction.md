The file `/app/data/reads.bam` is a coordinate-sorted BAM aligned
against the reference at `/app/data/ref.fa` (with index
`/app/data/ref.fa.fai`).

Produce two output files:

- `/app/output/reads.cram` — a CRAM file holding the **same** set of
  alignment records as the input BAM, compressed against the
  provided reference.
- `/app/output/reads.cram.crai` — an index for that CRAM.

Correctness means: if the CRAM is decoded back to text with
`samtools view /app/output/reads.cram`, and the BAM is decoded the
same way with `samtools view /app/data/reads.bam`, the two resulting
streams must contain the **same multiset of records** after sorting.
The grader compares only the 11 mandatory SAM columns (`QNAME`,
`FLAG`, `RNAME`, `POS`, `MAPQ`, `CIGAR`, `RNEXT`, `PNEXT`, `TLEN`,
`SEQ`, `QUAL`). Optional tag columns (`MD`, `NM`, …) and header
lines are ignored. Record order inside the CRAM does not need to
match the BAM byte for byte; the grader sorts both.

The output files must exist and must be non-empty.
