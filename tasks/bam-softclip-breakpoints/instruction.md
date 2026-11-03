`/app/data/clips.bam` (indexed) contains 100-base alignments, some of them
soft-clipped at a breakpoint.

Find the breakpoints that several reads agree on.

Use only alignments that are mapped and are not secondary (`0x100`), not
supplementary (`0x800`) and not duplicates (`0x400`). An alignment
contributes a breakpoint when its CIGAR begins or ends with a soft clip
(`S`) of **at least 10 bases**:

- a leading clip gives a `L` breakpoint at the alignment's leftmost
  reference position;
- a trailing clip gives a `R` breakpoint one base past the last aligned
  reference base.

Use 0-based reference positions, as `samtools` reports them internally.

Cluster breakpoints that share a chromosome and side and lie within 5 bases
of the previous position in the sorted cluster. Report only clusters with at
least three supporting reads.

Write `/app/output/breakpoints.tsv` with header

`chrom	side	position	n_reads`

where `position` is the cluster's median, taking the lower of the two middle
values when the count is even. Sort by chromosome, then position, then side.
