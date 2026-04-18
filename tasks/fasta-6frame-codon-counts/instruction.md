The file `/app/data/seqs.fa` is a multi-record nucleotide FASTA with
mixed-case sequences and a sprinkling of `N` characters.

Count DNA **codon occurrences across all 6 reading frames**:

- Treat each sequence as upper-case.
- Build its reverse complement (A<->T, C<->G). Keep N's as N's.
- On each strand consider three frames: frame 0 starts at position 0,
  frame 1 at 1, frame 2 at 2. Within a frame, codons are the
  successive **non-overlapping** 3-mers (`seq[i:i+3]` for i in
  {frame, frame+3, frame+6, ...}) as long as `i + 3 <= len(seq)`.
- A codon is counted only if all three bases are in `{A,C,G,T}`. Any
  codon containing `N` is skipped.

Sum counts across every sequence, every frame, and both strands.

Write `/app/output/codon_counts.tsv` with **exactly 64 lines**, one
per codon in the `ACGT` 3-letter space, sorted by codon ASCII
ascending (AAA first, TTT last), TAB-separated, no header:

    codon    count

Include codons with count 0. A trailing newline after TTT is fine.
Grading is exact diff against gold.
