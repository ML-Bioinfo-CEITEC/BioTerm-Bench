#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
from pathlib import Path

STOPS = {"TAA", "TAG", "TGA"}

header = None
seq_parts: list[str] = []
with open("/app/data/seq.fa") as fh:
    for line in fh:
        line = line.rstrip("\n")
        if line.startswith(">"):
            header = line[1:].split()[0]
        else:
            seq_parts.append(line.strip().upper())
seq = "".join(seq_parts)
L = len(seq)
assert header is not None, "no FASTA header"


def revcomp(s: str) -> str:
    return s.translate(str.maketrans("ACGTN", "TGCAN"))[::-1]


strands = [("+", seq), ("-", revcomp(seq))]
best = None  # tuple sorted ascending -> smallest == best
for strand_rank, (strand_label, oriented) in enumerate(strands):
    for frame in range(3):
        i = frame
        while i + 3 <= L:
            if oriented[i:i + 3] == "ATG":
                j = i + 3
                found_stop = False
                while j + 3 <= L:
                    if oriented[j:j + 3] in STOPS:
                        orf_len = j + 3 - i
                        if strand_rank == 0:
                            start_1b = i + 1
                            end_1b = j + 3
                        else:
                            end_1b = L - i
                            start_1b = L - (j + 3) + 1
                        key = (-orf_len, strand_rank, frame, start_1b)
                        if best is None or key < best[0]:
                            best = (key, strand_label, frame, start_1b, end_1b)
                        found_stop = True
                        i = j + 3
                        break
                    j += 3
                if not found_stop:
                    i += 3
            else:
                i += 3

assert best is not None, "no ORF found"
_, strand_label, frame, start_1b, end_1b = best
length = end_1b - start_1b + 1

with open("/app/output/orf.tsv", "w") as fh:
    fh.write("seq_id\tstrand\tframe\tstart\tend\tlength\n")
    fh.write(f"{header}\t{strand_label}\t{frame}\t{start_1b}\t{end_1b}\t{length}\n")
PY
