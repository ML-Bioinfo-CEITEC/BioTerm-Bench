`/app/data/annotation.gtf` has `gene`, `transcript`, `exon` and `CDS`
records on both strands. Every transcript has exons; only some have CDS.

For each transcript with at least one `CDS` record, reconstruct its
untranslated regions from the exon and CDS coordinates.

Let `cds_start` be that transcript's smallest CDS start and `cds_end` its
largest CDS end (GTF coordinates are 1-based inclusive). Exonic bases
strictly before `cds_start` form one UTR; exonic bases strictly after
`cds_end` form the other. On a `+` transcript the upstream side is the
5' UTR; on a `-` transcript it is the 3' UTR. `cds_len` is the total length
of the transcript's CDS records.

Only exonic bases count -- intronic gaps belong to no UTR.

Write `/app/output/utr_lengths.tsv` with header

`tx_id	gene_id	strand	utr5_len	utr3_len	cds_len`

one row per coding transcript, sorted by `tx_id`. Transcripts without CDS
must not appear.
