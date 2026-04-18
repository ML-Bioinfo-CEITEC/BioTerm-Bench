#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
BASES = "ACGT"
COMP = str.maketrans("ACGTN", "TGCAN")


def iter_fasta(path: str):
    name = None
    chunks: list[str] = []
    with open(path) as fh:
        for line in fh:
            line = line.rstrip()
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(chunks)
                name = line[1:].split()[0]
                chunks = []
            else:
                chunks.append(line)
    if name is not None:
        yield name, "".join(chunks)


counts = {a + b + c: 0 for a in BASES for b in BASES for c in BASES}

for _, seq in iter_fasta("/app/data/seqs.fa"):
    s = seq.upper()
    rc = s.translate(COMP)[::-1]
    for strand in (s, rc):
        n = len(strand)
        for frame in (0, 1, 2):
            i = frame
            while i + 3 <= n:
                cod = strand[i:i + 3]
                if cod in counts:
                    counts[cod] += 1
                i += 3

with open("/app/output/codon_counts.tsv", "w") as fh:
    for cod in sorted(counts):
        fh.write(f"{cod}\t{counts[cod]}\n")
PY
