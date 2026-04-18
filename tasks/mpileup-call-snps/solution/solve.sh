#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

bcftools mpileup \
    -f /app/data/reference.fa.gz \
    -q 20 -Q 20 --max-depth 1000 \
    /app/data/reads.bam \
  | bcftools call -mv --ploidy 1 -V indels \
        -Oz -o /app/output/calls.vcf.gz

tabix -f -p vcf /app/output/calls.vcf.gz
