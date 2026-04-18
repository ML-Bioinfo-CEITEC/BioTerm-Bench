The directory `/app/data/genomes/` contains 6 small FASTA files named
`genome_01.fa` ... `genome_06.fa`, each with a single record.

Compute all pairwise **Jaccard similarities** of canonical `k=15`
nucleotide k-mer sets:

- Upper-case the sequence before indexing.
- A k-mer is a length-15 substring of A/C/G/T only. Skip any window
  that contains a base outside `{A,C,G,T}` (e.g. N).
- Use the **canonical** form: for each k-mer, take the
  lexicographically smaller of (forward, reverse complement). Each
  canonical k-mer is counted once per genome.
- Jaccard(A, B) = |K_A ∩ K_B| / |K_A ∪ K_B|, with value 0 when the
  union is empty.

Write `/app/output/jaccard.tsv` with exactly three TAB-separated
columns, **no header**:

    genome_a    genome_b    jaccard

Emit each unordered pair exactly once, with `genome_a < genome_b`
ASCII. Rows sorted by `genome_a` ASCII ascending, then `genome_b`
ASCII ascending. `jaccard` must be formatted with exactly 6 decimals
(e.g. `0.042711`, `1.000000`).

Grading is numeric: the (genome_a, genome_b) pair set must match
gold exactly, and each `jaccard` value must be within `1e-5` of gold.
