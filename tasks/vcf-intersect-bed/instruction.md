The file `/app/data/calls.vcf.gz` (with index `.tbi`) is a bgzipped,
indexed VCF. The file `/app/data/regions.bed` is a 3-column BED
(chrom, 0-based start, end-exclusive) listing target regions on the
same contig.

Produce two output files:

- `/app/output/in_regions.vcf.gz` — a bgzipped VCF containing **only
  the records whose POS falls inside one of the regions** in
  `regions.bed`, using the standard half-open convention (a record
  at POS `p` is inside region `[start, end)` iff `start < p <= end`
  after converting POS to 0-based: i.e. `p - 1 >= start and p - 1 < end`,
  which is exactly what `bcftools view -R` does).
- `/app/output/in_regions.vcf.gz.tbi` — the tabix index for the
  output VCF.

Keep the original header (FILTER, INFO, contig lines etc.) and do
not reorder records. `bcftools view -R` with the provided BED
produces a correct answer.

Record uniqueness is compared via `bcftools isec` between your
output and the hidden gold; the grader expects zero private-to-A and
zero private-to-B records.
