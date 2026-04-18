#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

samtools view -C -T /app/data/ref.fa \
    -o /app/output/reads.cram /app/data/reads.bam

samtools index /app/output/reads.cram
