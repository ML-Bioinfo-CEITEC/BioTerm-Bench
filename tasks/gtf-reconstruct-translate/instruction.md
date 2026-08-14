The files `/app/data/genome.fa` and `/app/data/annot.gtf` describe a
small genome and GTF annotation. Reconstruct each transcript's spliced
**CDS** (not the full exon sequence) and translate it with the standard
genetic code.

Rules:

- use only transcripts that have at least one `CDS` row;
- concatenate CDS segments in transcript 5'→3' order;
- for `-` strand transcripts, reverse-complement after assembling the
  genomic CDS segments in transcript order;
- the CDS rows are already trimmed to coding bases; the phase column is
  consistent metadata and does not require extra trimming;
- translate the CDS in-frame; the gold data contain no internal stops.

Write `/app/output/proteins.tsv` with this header:

`transcript_id	gene_id	strand	cds_length	peptide_length	peptide`

Rows sorted by `transcript_id` ASCII ascending. `cds_length` is in
nucleotides, `peptide_length` is in amino acids, and a trailing newline
is required.

Grading is exact diff against the gold TSV.
