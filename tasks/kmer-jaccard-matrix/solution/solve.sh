#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
import os
from pathlib import Path

K = 15
COMP = str.maketrans("ACGT", "TGCA")


def read_fasta(path):
    chunks = []
    with open(path) as fh:
        for line in fh:
            if line.startswith(">"):
                continue
            chunks.append(line.strip())
    return "".join(chunks)


def canonical_kmers(seq, k):
    out = set()
    s = seq.upper()
    n = len(s)
    for i in range(n - k + 1):
        w = s[i:i + k]
        if any(b not in "ACGT" for b in w):
            continue
        rc = w.translate(COMP)[::-1]
        out.add(w if w < rc else rc)
    return out


data = Path("/app/data/genomes")
files = sorted(data.glob("*.fa"))
genomes = {p.stem: canonical_kmers(read_fasta(p), K) for p in files}
ids = sorted(genomes)

rows = []
for i in range(len(ids)):
    for j in range(i + 1, len(ids)):
        a, b = ids[i], ids[j]
        inter = len(genomes[a] & genomes[b])
        union = len(genomes[a] | genomes[b])
        j_val = inter / union if union else 0.0
        rows.append(f"{a}\t{b}\t{j_val:.6f}")

with open("/app/output/jaccard.tsv", "w") as fh:
    fh.write("\n".join(rows) + "\n")
PY
