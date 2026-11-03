`/app/data/annotation.gtf` annotates `/app/data/genome.fa`. Every
transcript has `exon` and `CDS` records.

Check each transcript's coding sequence and report what is wrong with it.

Build a transcript's CDS by taking its `CDS` records, ordering them along
the direction of transcription, extracting each from the genome, and
reverse-complementing every piece on a `-` strand transcript before
concatenating. GTF coordinates are 1-based inclusive.

Read codons from the start of that sequence. Then decide `status` by the
**first** of these that applies, in this order:

1. `not_multiple_of_three` -- the CDS length is not divisible by 3;
2. `no_start_codon` -- the first codon is not `ATG`;
3. `internal_stop` -- a stop codon (`TAA`, `TAG`, `TGA`) occurs anywhere
   before the final codon;
4. `no_stop_codon` -- the final codon is not a stop codon;
5. `ok`.

Write `/app/output/cds_report.tsv` with header

`tx_id	chrom	strand	cds_len	has_start	has_stop	n_internal_stops	status`

one row per transcript sorted by `tx_id`, with `has_start` and `has_stop`
as `yes` or `no` and `n_internal_stops` counting stop codons before the
final codon.
