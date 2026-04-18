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

  `present` is `1` if the k-mer occurs at least once in the forward
  strand of any sequence inside that FASTA, else `0`. Case-insensitive
  match against `ACGT` only (ignore `N` positions).

Rows must be sorted first by `genome_id` lexicographically, then by
`kmer` lexicographically. Every (genome, kmer) combination must appear
exactly once; no duplicates, no missing.
