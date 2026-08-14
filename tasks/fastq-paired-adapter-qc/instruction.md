The files `/app/data/reads_R1.fastq.gz` and `/app/data/reads_R2.fastq.gz` are gzipped paired-end FASTQs in Phred+33.

Pair reads by normalized ID: take the first whitespace-delimited token from the FASTQ header and drop a trailing `/1` or `/2`.

Using the exact adapter sequence `AGATCGGAAGAGC`, write:

- `/app/output/summary.json` with keys:
  `total_r1`, `total_r2`, `proper_pairs`, `orphan_r1`, `orphan_r2`,
  `adapter_pairs`, `adapter_pairs_both_mates`, `q30_frac_r1`, `q30_frac_r2`
- `/app/output/orphans.tsv` with header `read_id	present_in`

`proper_pairs` are IDs present in both files. Orphans are IDs present in only one file. `adapter_pairs` counts proper pairs where either mate contains the adapter substring; `adapter_pairs_both_mates` needs both mates. `q30_frac_*` is the fraction of bases with quality `>= 30` across proper-pair reads of that mate. Sort `orphans.tsv` by `read_id`.
