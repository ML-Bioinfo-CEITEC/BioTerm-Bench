The file `/app/data/in.fa` is a nucleotide FASTA. The file
`/app/data/map.tsv` is a two-column, tab-separated table with header
row `old_id\tnew_id` describing how to rename some of the sequence
headers.

Produce one output file:

- `/app/output/renamed.fa` — a FASTA in which every record's header
  line is exactly `>NEW_ID` (no description, no trailing whitespace),
  where `NEW_ID` is:
    - the `new_id` from `map.tsv` if the record's original id appears
      in `map.tsv`;
    - otherwise the record's original id, unchanged.

"Original id" is the first whitespace-delimited token of the input
header line (i.e. everything between `>` and the first space or tab,
or end of line). The description (anything after that token) is
dropped in the output.

Rules for the output file:

- Keep the sequence records in the **same order** as `in.fa`.
- Keep each sequence exactly as in `in.fa`, including the line-wrap
  width (60 bases per line).
- Do not emit blank lines.
- Every input record must appear in the output exactly once.
