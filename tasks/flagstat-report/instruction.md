The file `/app/data/reads.bam` is a coordinate-sorted BAM with a mix of
primary, supplementary, duplicate-flagged, and unmapped records.

Produce one output file:

- `/app/output/metrics.tsv` — a two-column, tab-separated, headerless
  TSV. Column 1 is the metric name; column 2 is the integer count
  reported by `samtools flagstat` as the primary (QC-passed) count.
  Rows must be sorted alphabetically by metric name.

The five metric rows required, with exactly these names in column 1:

    duplicates
    mapped
    properly_paired
    supplementary
    total_reads

`total_reads` is flagstat's "in total" line; the others are the
corresponding flagstat lines named similarly.
