The file `/app/data/reads.fastq.gz` is a gzipped FASTQ of
single-end reads of varying lengths.

Produce one output file:

- `/app/output/lengths.tsv` — tab-separated with a header row
  `length\tcount`. Each subsequent row has two integer columns:
    - `length`: a read length (in bases) that occurs in the file,
    - `count`: how many reads in the file have exactly that length.

Rules:

- Only include lengths that actually occur (do not pad zero-count
  rows for absent lengths).
- Rows sorted by `length` ascending (numerically).
- "Length of a read" is the number of characters on the
  sequence line of that FASTQ record (equivalently, the length of
  the 2nd line of each 4-line record).
- The sum of all `count` values must equal the total number of reads
  in the file.
- No blank lines, no trailing whitespace.
