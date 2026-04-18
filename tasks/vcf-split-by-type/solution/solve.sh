#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

bcftools view -v snps -Oz \
    -o /app/output/snps.vcf.gz /app/data/variants.vcf.gz
bcftools view -v indels -Oz \
    -o /app/output/indels.vcf.gz /app/data/variants.vcf.gz

tabix -f -p vcf /app/output/snps.vcf.gz
tabix -f -p vcf /app/output/indels.vcf.gz
