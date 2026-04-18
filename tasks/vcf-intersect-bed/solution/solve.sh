#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

bcftools view -R /app/data/regions.bed \
    -Oz -o /app/output/in_regions.vcf.gz /app/data/calls.vcf.gz

tabix -f -p vcf /app/output/in_regions.vcf.gz
