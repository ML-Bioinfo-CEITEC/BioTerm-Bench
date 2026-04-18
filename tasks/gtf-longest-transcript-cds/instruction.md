The file `/app/data/annot.gtf` is a GENCODE-style GTF with `gene`,
`transcript`, `exon`, and `CDS` feature rows. Some transcripts have
CDS annotation, some do not; some genes have no CDS-bearing transcript
at all.

For each **gene** that has at least one transcript with at least one
`CDS` feature, select the transcript whose **total CDS length** is
largest. Total CDS length is the sum over that transcript's `CDS`
features of `end - start + 1` (GTF is 1-based, inclusive on both
ends). Ties are broken by `transcript_id` ASCII ascending.

Write the result to `/app/output/longest_cds.tsv` with exactly four
TAB-separated columns, **no header**:

    gene_id    transcript_id    cds_length    n_cds_features

Rows sorted by `gene_id` ASCII ascending. Trailing newline after the
final row. Genes without any CDS-bearing transcript are **not**
emitted.

Grading is exact diff against the gold file — whitespace, column
order, sort order, and row count must all match.
