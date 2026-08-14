The file `/app/data/annot.gtf` is an exon-level annotation, and
`/app/data/sample_A.bam` through `/app/data/sample_D.bam` are
coordinate-sorted **single-end reverse-stranded** RNA-seq BAMs.

Count exon-overlapping reads per `gene_id` with exon-union semantics.
Use the four BAMs in the sample order `sample_A`, `sample_B`,
`sample_C`, `sample_D`.

Write two TAB-separated outputs:

- `/app/output/gene_counts.tsv` with header
  `gene_id<TAB>sample_A<TAB>sample_B<TAB>sample_C<TAB>sample_D`
- `/app/output/assignment_summary.tsv` with header
  `status<TAB>sample_A<TAB>sample_B<TAB>sample_C<TAB>sample_D`

`gene_counts.tsv` must contain one row per annotated gene, in the same
gene order as the annotation. `assignment_summary.tsv` must contain
exactly these three rows, in this order:

1. `Assigned`
2. `Unassigned_NoFeatures`
3. `Unassigned_Unmapped`

All count values are integers. End each file with a trailing newline.
