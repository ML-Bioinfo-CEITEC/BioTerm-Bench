You are given two tab-separated files.

- `/app/data/input.tsv` — a single column `query_symbol` with one gene
  symbol per row (header present). Entries may be current HGNC
  symbols, previously-used aliases, or unknown.
- `/app/data/hgnc.tsv` — a curated mini-HGNC table with columns
  `hgnc_id`, `symbol`, `aliases`, `ensembl_gene_id` (header present).
  `symbol` is the current HGNC-approved symbol. `aliases` is a
  `|`-separated list of previous symbols / known aliases (possibly
  empty). `ensembl_gene_id` is the canonical ENSG identifier. Current
  symbols are unique; aliases never collide with current symbols or
  with each other.

Write the mapping to `/app/output/mapping.tsv` with exactly these
four columns in order (header required):

    query_symbol    resolved_symbol    ensembl_gene_id    status

Semantics:

- If `query_symbol` matches a current HGNC `symbol` exactly, set
  `resolved_symbol` and `ensembl_gene_id` from that row and set
  `status = "exact"`.
- Else if `query_symbol` matches one of the `aliases`, set
  `resolved_symbol` and `ensembl_gene_id` from that row and set
  `status = "alias"`.
- Otherwise write `query_symbol` unchanged, leave `resolved_symbol`
  and `ensembl_gene_id` empty, and set `status = "not_found"`.

Rows must be sorted alphabetically by `query_symbol` (case-sensitive
ASCII order). Lookup is case-sensitive.
