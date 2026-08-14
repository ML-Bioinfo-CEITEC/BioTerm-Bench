#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
from collections import defaultdict
from pathlib import Path


def revcomp(seq: str) -> str:
    return seq.translate(str.maketrans("ACGT", "TGCA"))[::-1]


refs = {}
cur = None
buf = []
with open("/app/data/references.fa") as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if cur is not None:
                refs[cur] = "".join(buf)
            cur = line[1:].split()[0]
            buf = []
        else:
            buf.append(line.upper())
if cur is not None:
    refs[cur] = "".join(buf)

reads = []
with open("/app/data/reads.fastq") as fh:
    while True:
        name = fh.readline().rstrip("\n")
        if not name:
            break
        seq = fh.readline().rstrip("\n").upper()
        fh.readline()
        fh.readline()
        reads.append(seq)

unique = defaultdict(int)
ambig = defaultdict(float)
weighted = defaultdict(float)
for seq in reads:
    rc = revcomp(seq)
    hits = [rid for rid, ref in refs.items() if seq in ref or rc in ref]
    if not hits:
        continue
    share = 1.0 / len(hits)
    if len(hits) == 1:
        unique[hits[0]] += 1
    else:
        for rid in hits:
            ambig[rid] += share
    for rid in hits:
        weighted[rid] += share

denom = sum(weighted[rid] / len(refs[rid]) for rid in refs)
with open("/app/output/abundance.tsv", "w") as fh:
    fh.write(
        "reference_id\tlength_bp\tunique_reads\tambiguous_weight\tweighted_reads\trel_abundance_ppm\n"
    )
    for rid in sorted(refs):
        rel = 1e6 * (weighted[rid] / len(refs[rid])) / denom
        fh.write(
            f"{rid}\t{len(refs[rid])}\t{unique[rid]}\t{ambig[rid]:.4f}\t"
            f"{weighted[rid]:.4f}\t{rel:.6f}\n"
        )
PY
