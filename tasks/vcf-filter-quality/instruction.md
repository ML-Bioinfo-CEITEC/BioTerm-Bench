The file `/app/data/calls.vcf.gz` is a bgzip-compressed, tabix-indexed
VCF with varying `QUAL` and `INFO/DP` values.

Produce one output file:

- `/app/output/passed.vcf.gz` — a bgzip-compressed, tabix-indexed VCF
  containing only the records whose `QUAL >= 30` AND `INFO/DP >= 10`.

The input header must be preserved (subsequent `##FILTER` lines may be
added but the original contigs and INFO tags must remain). Output does
not need to be sorted beyond the input's order. A `.tbi` next to the
output VCF is also required.
