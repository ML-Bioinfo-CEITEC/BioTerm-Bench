The files `/app/data/annot.gtf` and `/app/data/reads.bam` describe a
small annotated gene set and coordinate-sorted RNA-seq alignments.

Derive annotated splice junctions from each transcript's consecutive
`exon` rows in transcript 5'→3' order. For each adjacent exon pair,
define the intron as:

- `intron_start = left_exon_end + 1`
- `intron_end   = right_exon_start - 1`

Count supporting reads in `/app/data/reads.bam` using only primary,
mapped alignments. Every `N` CIGAR op contributes one observed junction
at its exact skipped reference interval. If one read has two `N` ops, it
can support two different annotated junctions.

Write `/app/output/support.tsv` with this header:

`gene_id	transcript_id	junction_index	chrom	intron_start	intron_end	support_reads`

Rules:

- one row for every annotated junction, even if support is 0;
- `junction_index` is 1-based in transcript 5'→3' order;
- rows sorted by `transcript_id` ASCII ascending, then `junction_index`;
- trailing newline required.

Grading is exact diff against the gold TSV.
