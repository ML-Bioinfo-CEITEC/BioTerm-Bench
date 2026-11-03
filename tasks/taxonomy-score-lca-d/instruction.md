`/app/data/case.json` contains the complete input for this candidate and an
`operation` field equal to `taxonomy_lca`. Keep hits scoring at least the configured fraction of each query's best score, deduplicate their taxa, and report their lowest common ancestor in the supplied taxonomy.

Parameters for this fixture: fraction=0.87, input_schema=parent: taxon to parent; rank: taxon to rank; queries: [query_id, [[taxon, score], ...]].
Do not assume records are pre-sorted unless the requested output order says so.

Write `/app/output/result.tsv`. The exact required header is documented in
`/app/data/output_header.txt`. Emit rows in this order: input query order.
Numeric output may contain additional precision.
