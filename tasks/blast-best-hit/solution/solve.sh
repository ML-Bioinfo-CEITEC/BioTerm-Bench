#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

# tab-delimited best hit per query, max_target_seqs=1 + max_hsps=1
blastp \
    -query /app/data/queries.fasta \
    -db /opt/references/blast_db/kinome \
    -outfmt '6 qseqid sseqid bitscore evalue' \
    -max_target_seqs 1 -max_hsps 1 \
    -num_threads 2 \
    > /tmp/raw_hits.tsv

python3 - <<'PY' > /app/output/best_hits.tsv
from collections import defaultdict

best = {}  # qid -> (bitscore, evalue, sseqid)
with open("/tmp/raw_hits.tsv") as fh:
    for line in fh:
        qid, sseqid, bitscore, evalue = line.rstrip("\n").split("\t")
        bitscore = float(bitscore)
        evalue = float(evalue)
        prev = best.get(qid)
        cand = (bitscore, -evalue, sseqid)
        if prev is None or cand > (prev[0], -prev[1], prev[2]):
            best[qid] = (bitscore, evalue, sseqid)

with open("/app/data/queries.fasta") as fh:
    queries = [line[1:].split()[0] for line in fh if line.startswith(">")]

for q in sorted(queries):
    sseqid = best.get(q, (0, 0, "NO_HIT"))[2]
    # Normalise: strip trailing pipes/versions after last dot
    sseqid = sseqid.rstrip("|")
    print(f"{q}\t{sseqid}")
PY
