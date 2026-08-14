The files `/app/data/ref.fa`, `/app/data/reads_1.fastq.gz`,
`/app/data/reads_2.fastq.gz`, and `/app/data/targets.bed` define a small
paired-end resequencing experiment.

Align the reads to the reference, call small variants, left-align and
normalize them against the same reference, then keep only unfiltered
records whose `POS` overlaps at least one BED interval in `targets.bed`.

Write:

- `/app/output/final.vcf.gz` — bgzip-compressed VCF with the filtered,
  normalized calls.
- `/app/output/final.vcf.gz.tbi` — tabix index for that VCF.

The output must stay coordinate-sorted, preserve a valid VCF header, and
contain only records from `chrMini`. The grader compares the resulting
variant set exactly and also rejects records outside the target intervals
or with any filter other than `.` or `PASS`.
