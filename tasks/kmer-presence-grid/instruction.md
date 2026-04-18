Build a presence-grid of k-mers against a small collection of genomes.

Input:

- `/app/data/genomes/` — directory of small FASTA files. Each file has
  a `.fa` suffix; the `genome_id` is the file stem (e.g. `genome_01.fa`
  -> `genome_01`).
- `/app/data/kmers.txt` — one k-mer per line (ACGT only, uppercase,
  all the same length).

Produce one output file:

- `/app/output/presence.tsv` — a tab-separated TSV with three columns
  and no header:

      genome_id   kmer   present

  `present` is `1` if the k-mer occurs at least once as a contiguous
  substring of the concatenation of all sequences inside that FASTA
  (forward strand, case-insensitive), else `0`. Do not reverse-
  complement. The k-mers themselves contain only `A C G T`.

Rows must be sorted first by `genome_id` lexicographically, then by
`kmer` lexicographically. Every (genome, kmer) combination must appear
exactly once; no duplicates, no missing.
