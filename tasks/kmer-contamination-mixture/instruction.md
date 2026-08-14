The directory `/app/data/references/` contains four small reference
genomes (`alpha.fa`, `beta.fa`, `gamma.fa`, `delta.fa`) and
`/app/data/reads.fastq.gz` contains a mixed sample.

Using canonical nucleotide `k=17` k-mers, estimate the mixture as
follows:

- A reference-specific k-mer is present in exactly one reference.
- For each read, count how many reference-specific canonical 17-mers it
  matches from each reference.
- Assign the read to the single reference with the highest count.
- If the top count is tied between multiple references, label the read
  `ambiguous`.
- If every reference score is zero, label the read `unassigned`.

Write `/app/output/mixture.tsv` with header
`label<TAB>read_count<TAB>fraction`, rows ordered exactly as
`alpha`, `beta`, `gamma`, `delta`, `ambiguous`, `unassigned`. Format
`fraction` as `read_count / total_reads` with exactly 4 decimals.
