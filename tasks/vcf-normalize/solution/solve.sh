#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

bcftools norm -m -any -f /app/data/ref.fa /app/data/unnorm.vcf.gz \
    | bcftools sort -Oz -o /app/output/norm.vcf.gz -

tabix -f -p vcf /app/output/norm.vcf.gz
