#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

sort -k1,1 -k2,2n /app/data/intervals.bed \
    | bedtools merge -d 50 -i - \
    > /app/output/merged.bed
