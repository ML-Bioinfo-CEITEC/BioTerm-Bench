#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output
samtools view -b /app/data/all_reads.bam 22:16000000-17000000 \
    > /app/output/region_reads.bam
