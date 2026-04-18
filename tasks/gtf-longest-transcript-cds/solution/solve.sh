#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
import re
from collections import defaultdict

ATTR_RE = re.compile(r'(\w+)\s+"([^"]+)"')

cds_len = defaultdict(int)     # tid -> total CDS length
cds_count = defaultdict(int)   # tid -> number of CDS features
tid_gene = {}                  # tid -> gene_id

with open("/app/data/annot.gtf") as fh:
    for line in fh:
        if not line.strip() or line.startswith("#"):
            continue
        fields = line.rstrip("\n").split("\t")
        if len(fields) < 9 or fields[2] != "CDS":
            continue
        attrs = dict(ATTR_RE.findall(fields[8]))
        gid = attrs.get("gene_id")
        tid = attrs.get("transcript_id")
        if not gid or not tid:
            continue
        start = int(fields[3])
        end = int(fields[4])
        cds_len[tid] += end - start + 1
        cds_count[tid] += 1
        tid_gene[tid] = gid

best = {}  # gene_id -> (tid, cds_len, n_cds)
for tid, gid in tid_gene.items():
    cl = cds_len[tid]
    nc = cds_count[tid]
    cur = best.get(gid)
    if cur is None or cl > cur[1] or (cl == cur[1] and tid < cur[0]):
        best[gid] = (tid, cl, nc)

with open("/app/output/longest_cds.tsv", "w") as fh:
    for gid in sorted(best):
        tid, cl, nc = best[gid]
        fh.write(f"{gid}\t{tid}\t{cl}\t{nc}\n")
PY
