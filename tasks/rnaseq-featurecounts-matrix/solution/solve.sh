#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

tmp="/tmp/featurecounts.tsv"
featureCounts \
  -T 1 \
  -a /app/data/annot.gtf \
  -o "${tmp}" \
  -t exon \
  -g gene_id \
  -s 2 \
  /app/data/sample_A.bam \
  /app/data/sample_B.bam \
  /app/data/sample_C.bam \
  /app/data/sample_D.bam \
  >/tmp/featurecounts.stdout 2>/tmp/featurecounts.stderr

python3 - <<'PY'
import csv
from pathlib import Path

raw = Path("/tmp/featurecounts.tsv")
summary = Path("/tmp/featurecounts.tsv.summary")

with raw.open() as fh, open("/app/output/gene_counts.tsv", "w") as out_fh:
    reader = csv.reader((line for line in fh if not line.startswith("#")), delimiter="\t")
    header = next(reader)
    out_fh.write("gene_id\tsample_A\tsample_B\tsample_C\tsample_D\n")
    for row in reader:
        out_fh.write(row[0] + "\t" + "\t".join(row[6:]) + "\n")

wanted = ["Assigned", "Unassigned_NoFeatures", "Unassigned_Unmapped"]
summary_rows = {}
with summary.open() as fh:
    reader = csv.reader(fh, delimiter="\t")
    next(reader)
    for row in reader:
        summary_rows[row[0]] = row[1:]

with open("/app/output/assignment_summary.tsv", "w") as out_fh:
    out_fh.write("status\tsample_A\tsample_B\tsample_C\tsample_D\n")
    for key in wanted:
        out_fh.write(key + "\t" + "\t".join(summary_rows[key]) + "\n")
PY
