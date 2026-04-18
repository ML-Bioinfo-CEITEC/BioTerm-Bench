#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
WIN = 100
STEP = 50


def iter_fasta(path):
    name = None
    chunks = []
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


records = list(iter_fasta("/app/data/seqs.fa"))

rows = []
for sid, seq in sorted(records, key=lambda kv: kv[0]):
    s = seq.upper()
    n = len(s)
    start = 0
    while start + WIN <= n:
        end = start + WIN
        w = s[start:end]
        gc = sum(1 for b in w if b in "GC")
        pct = round(100.0 * gc / len(w), 2)
        rows.append(f"{sid}\t{start}\t{end}\t{pct:.2f}")
        start += STEP

with open("/app/output/gc_windows.tsv", "w") as fh:
    fh.write("\n".join(rows) + "\n")
PY
