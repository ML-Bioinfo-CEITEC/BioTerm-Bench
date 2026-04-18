The file `/app/data/variants.vcf.gz` is a bgzip-compressed, tabix-indexed
VCF holding a mix of SNVs and indels, all bi-allelic.

Split it by variant type and produce two output files:

- `/app/output/snps.vcf.gz`   — only SNV records (REF and ALT both
  length 1). Bgzipped and tabix-indexed.
- `/app/output/indels.vcf.gz` — only indel records (REF and ALT have
  different lengths, and are not both length 1). Bgzipped and
  tabix-indexed.

Every input record must end up in exactly one of the two outputs. The
input header (contigs, INFO tags) must be preserved in both outputs.
