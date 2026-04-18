The directory `/app/data/` contains:

- `reads.bam` — coordinate-sorted, indexed reads aligned against the
  SARS-CoV-2 reference.
- `reference.fa.gz` — the SARS-CoV-2 reference (bgzipped, with
  `.fai` and `.gzi` sidecars).

Call bi-allelic SNP variants with bcftools using exactly these flags,
so that the result is reproducible:

    bcftools mpileup -f reference.fa.gz -q 20 -Q 20 --max-depth 1000 \
        reads.bam \
      | bcftools call -mv --ploidy 1 -V indels -Oz -o calls.vcf.gz

Then tabix-index the output.

Produce:

- `/app/output/calls.vcf.gz`
- `/app/output/calls.vcf.gz.tbi`

Only SNP calls must be present (indels suppressed). The output will be
compared against a gold VCF by `bcftools isec`.
