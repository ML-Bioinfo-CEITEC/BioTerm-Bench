The file `/app/data/genes.gtf` is a small GENCODE-style GTF slice
from human chr22 containing records for several genes (gene,
transcript, exon, CDS, …).

Produce one output file:

- `/app/output/gene_lengths.tsv` — tab-separated with a header row
  `gene_id\tlength`, then one row per distinct `gene_id` in the GTF.
  `length` is the integer **union** length of that gene's exons:
  the number of distinct base positions covered by at least one
  `exon` feature for that gene.

Rules:

- Only GTF lines with feature type `exon` contribute to the length.
- GTF coordinates are **1-based, inclusive on both ends**. A record
  with start=10 and end=20 therefore covers 11 bases (positions
  10..20).
- Overlapping exons (e.g. shared between multiple transcripts of the
  same gene) must be counted **once**, not multiple times.
- Exons on different strands of the same `gene_id`, if any, are still
  unioned in genomic coordinate space.
- Rows sorted ascending by `gene_id` (ASCII), header first.
- No blank lines, no trailing whitespace.
