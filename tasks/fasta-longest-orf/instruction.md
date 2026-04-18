The file `/app/data/seq.fa` is a single-record nucleotide FASTA
(ACGT only, uppercase).

Find the **longest open reading frame** in the sequence under the
following strict definition:

- Consider all **six** reading frames (three forward, three on the
  reverse complement).
- An ORF begins at an `ATG` start codon and ends at the **first
  in-frame stop codon** (`TAA`, `TAG`, or `TGA`) that follows it.
- The ORF's start and end span from the first base of the `ATG` to
  the last base of the stop codon, inclusive (1-based, closed at
  both ends, in forward-strand coordinates).
- Length is `end - start + 1` (nucleotides, includes the stop).
- If two ORFs have the same length, prefer (in order):
  `+` strand before `-`, smaller frame (0, 1, 2), smaller `start`.

Produce one output file:

- `/app/output/orf.tsv` — tab-separated, two lines total:

        seq_id	strand	frame	start	end	length
        <id>	+|-	0|1|2	<int>	<int>	<int>

  `seq_id` is the first whitespace-delimited token of the FASTA
  header. `frame` is 0, 1 or 2 (the 0-based offset into the
  oriented strand at which the ORF starts). No extra whitespace, no
  blank lines.
