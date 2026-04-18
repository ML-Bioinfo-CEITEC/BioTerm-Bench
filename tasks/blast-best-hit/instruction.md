The file `/app/data/queries.fasta` contains a small set of protein
query sequences. A pre-built protein BLAST database, the UniProt human
kinome in Swiss-Prot, lives at `/opt/references/blast_db/kinome`.

For each query, run `blastp` against that database and report the best
hit. The winning hit is picked by (in this order):

  1. highest `bitscore`,
  2. lowest `evalue`,
  3. smallest `sseqid` by ASCII string order.

Produce one output file:

- `/app/output/best_hits.tsv` — a two-column tab-separated TSV with
  these columns and no header:

      query_id   best_subject

  `query_id` is the FASTA identifier (the token after `>` up to the
  first whitespace). `best_subject` is the BLAST `sseqid` of the top
  hit, stripped of trailing pipes and version suffixes if any.

Rows must be sorted alphabetically by `query_id`. Every query in the
input must appear as exactly one row (no missing, no duplicates).
