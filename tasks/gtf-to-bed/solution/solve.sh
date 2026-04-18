#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

awk 'BEGIN{FS=OFS="\t"}
     $0 ~ /^#/ {next}
     $3 == "exon" {
         gene_id = ""
         n = split($9, attrs, ";")
         for (i = 1; i <= n; i++) {
             sub(/^ +/, "", attrs[i])
             if (index(attrs[i], "gene_id ") == 1) {
                 gene_id = substr(attrs[i], 9)
                 gsub(/"/, "", gene_id)
                 break
             }
         }
         print $1, $4 - 1, $5, gene_id, ".", $7
     }' /app/data/genes.gtf \
  | sort -k1,1 -k2,2n -k3,3n -k4,4 \
  > /app/output/exons.bed
