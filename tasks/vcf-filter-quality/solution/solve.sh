#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

bcftools view -e 'QUAL<30 || INFO/DP<10' -Oz \
    -o /app/output/passed.vcf.gz /app/data/calls.vcf.gz
tabix -f -p vcf /app/output/passed.vcf.gz
