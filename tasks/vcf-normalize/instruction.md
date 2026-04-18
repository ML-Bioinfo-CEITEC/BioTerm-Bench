The file `/app/data/unnorm.vcf.gz` (with index `.tbi`) is a VCF
against the reference at `/app/data/ref.fa` (with `.fai`). It
contains at least one multi-allelic record (two or more ALTs on one
line) and at least one indel that is **not left-aligned**.

Produce two output files:

- `/app/output/norm.vcf.gz` — a bgzipped VCF equivalent to the input
  after it has been:
    1. **Split** so that every record has exactly one ALT
       (multi-allelic records become multiple records, one per ALT).
    2. **Left-aligned and parsimonious-trimmed** against `ref.fa`.
  Positional sort by `CHROM, POS` after splitting/normalization.
- `/app/output/norm.vcf.gz.tbi` — the tabix index for that VCF.

`bcftools norm -m -any -f /app/data/ref.fa` followed by
`bcftools sort -Oz -o norm.vcf.gz` and `tabix -p vcf norm.vcf.gz`
produces a correct answer.

Grading compares your output to a hidden gold via `bcftools isec`
and requires zero private-to-A and zero private-to-B records. The
header may differ in auxiliary lines; only records matter.
