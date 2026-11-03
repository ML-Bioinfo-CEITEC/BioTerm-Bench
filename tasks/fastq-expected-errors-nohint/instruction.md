`/app/data/reads.fastq` holds 2000 reads with Phred+33 quality encoding, so
a quality character's score is its ASCII value minus 33.

Report the reads whose expected number of sequencing errors exceeds 1.

A base with Phred score `Q` has error probability `P = 10 ** (-Q / 10)`.

- `mean_q` is the plain arithmetic mean of the read's Phred scores.
- `expected_errors` is the **sum** of the read's per-base error
  probabilities.
- `equivalent_q` is `-10 * log10(mean_error_probability)`, where the mean
  error probability is `expected_errors` divided by the read length.

Keep only reads with `expected_errors` greater than 1.0.

Write `/app/output/noisy_reads.tsv` with header

`read_id	length	mean_q	expected_errors	equivalent_q`

sorted by descending `expected_errors` then by `read_id`, with the three
computed columns to four decimals.
