The file `/app/data/all_reads.bam` is a coordinate-sorted, indexed BAM
of reads aligned against human chromosome 22 (reference name `22`).

Produce one output file:

- `/app/output/region_reads.bam` — a BAM containing every read that
  overlaps the interval `22:16000000-17000000` (1-based, inclusive
  endpoints as BAM regions are normally interpreted).

The output BAM must be coordinate-sorted and must carry the same
reference header information as the input. It does not need to be
indexed.
