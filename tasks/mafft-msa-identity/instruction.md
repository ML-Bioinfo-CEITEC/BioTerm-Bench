The file `/app/data/seqs.fa` is a multi-FASTA of 5 related
nucleotide sequences (each ~1.2 kb).

Align the five sequences with a multiple sequence aligner of your
choice (`mafft --auto /app/data/seqs.fa` produces the gold
alignment), then compute the pairwise percent identity for every
**unordered pair** of sequences using this exact definition:

    identity = matches / denom

where, for a pair of aligned sequences A and B:
  - `matches` is the number of MSA columns where A and B have the
    same non-gap character,
  - `denom` is the number of columns where **at least one of A or B
    is non-gap** (columns where both are gaps are ignored).

Produce one output file:

- `/app/output/identity.tsv` — tab-separated with header
  `seq_a\tseq_b\tidentity`. One row per unordered pair (C(5,2) = 10
  rows total). Rows sorted by `seq_a` then `seq_b` lexicographically;
  within each row `seq_a < seq_b` (also lexicographically).
  `identity` is a float in `[0.0, 1.0]`.

Use 6 decimal places (`{:.6f}`) when writing identity. Tolerance on
identity values is small but non-zero, so another aligner's output
will generally not score within tolerance.
