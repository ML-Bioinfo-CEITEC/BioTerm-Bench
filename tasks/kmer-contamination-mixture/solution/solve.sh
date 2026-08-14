#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
import gzip
from pathlib import Path

K = 17
COMP = str.maketrans("ACGT", "TGCA")
BASES = set("ACGT")
ORDER = ["alpha", "beta", "gamma", "delta", "ambiguous", "unassigned"]


def revcomp(seq: str) -> str:
    return seq.translate(COMP)[::-1]


def read_fasta(path: Path) -> str:
    parts = []
    with path.open() as fh:
        for line in fh:
            if not line.startswith(">"):
                parts.append(line.strip())
    return "".join(parts)


def canonical_kmers(seq: str) -> set[str]:
    seq = seq.upper()
    out = set()
    for i in range(len(seq) - K + 1):
        kmer = seq[i:i + K]
        if set(kmer) <= BASES:
            out.add(min(kmer, revcomp(kmer)))
    return out


refs = {
    p.stem: read_fasta(p)
    for p in sorted(Path("/app/data/references").glob("*.fa"))
}
ref_sets = {name: canonical_kmers(seq) for name, seq in refs.items()}
owners = {}
for name, kmers in ref_sets.items():
    for kmer in kmers:
        owners.setdefault(kmer, set()).add(name)
specific = {
    name: {kmer for kmer in kmers if owners[kmer] == {name}}
    for name, kmers in ref_sets.items()
}

counts = {name: 0 for name in ORDER}
reads = []
with gzip.open("/app/data/reads.fastq.gz", "rt") as fh:
    while True:
        name = fh.readline()
        if not name:
            break
        seq = fh.readline().strip().upper()
        fh.readline()
        fh.readline()
        reads.append(seq)

for read in reads:
    scores = {name: 0 for name in refs}
    for i in range(len(read) - K + 1):
        kmer = read[i:i + K]
        if set(kmer) - BASES:
            continue
        ck = min(kmer, revcomp(kmer))
        for name in refs:
            if ck in specific[name]:
                scores[name] += 1
    best = max(scores.values())
    if best == 0:
        counts["unassigned"] += 1
        continue
    winners = sorted(name for name, score in scores.items() if score == best)
    if len(winners) != 1:
        counts["ambiguous"] += 1
        continue
    counts[winners[0]] += 1

with open("/app/output/mixture.tsv", "w") as fh:
    fh.write("label\tread_count\tfraction\n")
    total = len(reads)
    for label in ORDER:
        fh.write(f"{label}\t{counts[label]}\t{counts[label] / total:.4f}\n")
PY
