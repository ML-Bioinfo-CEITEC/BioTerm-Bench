The file `/app/data/genes.gtf` is a GTF (GFF2) file describing genes on
human chromosome 22.

Produce one output file:

- `/app/output/exons.bed` — a BED6 TSV containing one row for every
  GTF record whose feature type is `exon`, with these columns:

      chrom  start  end  name  score  strand

  - `chrom` is the GTF seqname (column 1) unchanged.
  - `start` is `GTF_start - 1` (BED is 0-based, half-open).
  - `end` is the GTF end unchanged.
  - `name` is the `gene_id` value from the GTF attribute column,
    quotes stripped.
  - `score` must be the literal character `.`.
  - `strand` is the GTF strand (column 7).

Rows must be sorted by `chrom` lexicographically, then by `start`
ascending, then by `end` ascending, then by `name` lexicographically.
No header line; no trailing blank line. Duplicate rows (same six
columns) must be kept, not collapsed.
