#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

samtools sort -@ 2 -o /app/output/sample.sorted.bam /app/data/unsorted.sam
samtools index /app/output/sample.sorted.bam
