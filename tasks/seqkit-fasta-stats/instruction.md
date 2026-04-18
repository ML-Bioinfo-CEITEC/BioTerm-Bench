The file `/app/data/sequences.fa` is a plain-text FASTA file with one
or more sequences. Sequence IDs are the first whitespace-separated
token on each header line.

Produce one output file:

- `/app/output/stats.tsv` — a tab-separated TSV with a header row
  followed by exactly one row per FASTA sequence, in the same order
  as the input FASTA. Header (literal):

      seq_id    length    gc_percent    n_percent

  Semantics:

  - `seq_id` is the FASTA ID (first whitespace-separated token after
    the `>` on the header line).
  - `length` is the total number of characters in the sequence after
    joining wrapped lines and stripping whitespace.
  - `gc_percent` is the percentage of G+C bases (case-insensitive)
    over `length`, formatted with exactly two digits after the
    decimal point (e.g. `51.23`).
  - `n_percent` is the percentage of `N` bases (case-insensitive)
    over `length`, same formatting as `gc_percent`.

No trailing blank line. All values are exact-match (byte-identical)
comparison against the gold file.
