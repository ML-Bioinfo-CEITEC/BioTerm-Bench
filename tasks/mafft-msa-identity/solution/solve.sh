#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

mafft --auto --quiet /app/data/seqs.fa > /tmp/aligned.fa

python3 - <<'PY'
from pathlib import Path

records: dict[str, str] = {}
cur = None
buf: list[str] = []
with open("/tmp/aligned.fa") as fh:
    for line in fh:
        line = line.rstrip("\n")
        if line.startswith(">"):
            if cur is not None:
                records[cur] = "".join(buf).upper()
            cur = line[1:].split()[0]
            buf = []
        else:
            buf.append(line.strip())
if cur is not None:
    records[cur] = "".join(buf).upper()


def identity(a: str, b: str) -> float:
    m = d = 0
    for ca, cb in zip(a, b):
        if ca == "-" and cb == "-":
            continue
        d += 1
        if ca == cb:
            m += 1
    return m / d if d else 0.0


ids = sorted(records.keys())
with open("/app/output/identity.tsv", "w") as fh:
    fh.write("seq_a\tseq_b\tidentity\n")
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            fh.write(f"{a}\t{b}\t{identity(records[a], records[b]):.6f}\n")
PY
