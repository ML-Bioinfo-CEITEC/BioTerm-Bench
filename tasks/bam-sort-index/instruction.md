The file `/app/data/unsorted.sam` is an unsorted SAM file of reads
aligned to a small reference.

Produce two output files:

- `/app/output/sample.sorted.bam` — the same alignments in a
  coordinate-sorted BAM.
- `/app/output/sample.sorted.bam.bai` — a BAM index for the sorted file.

The sorted BAM must pass `samtools quickcheck`, its header's `SO` tag
must be `coordinate`, and the index must be readable by `samtools idxstats`.
The number of records in the output must equal the number of records in
the input.
