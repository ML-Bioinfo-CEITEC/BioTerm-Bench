#!/usr/bin/env python3
"""Generate a small multi-FASTA of related sequences + gold identity matrix.

We take a ~1.2 kb chunk of SARS-CoV-2 and derive 5 related "accessions"
from it by introducing a deterministic number of substitutions into
each copy. Then we MAFFT-align the 5 sequences and compute pairwise
percent identity as:

    identity = matches / (matches + mismatches + gaps)

where the denominator is the number of MSA columns where **at least
one** of the two sequences has a non-gap character. Identity is in
[0, 1].

Writes:
  /out/data/seqs.fa            5 sequences, ~1.2 kb each
  /out/gold/identity.tsv       upper triangle, sorted (seq_a, seq_b)
                               columns: seq_a  seq_b  identity
"""
from __future__ import annotations

import gzip
import random
import subprocess
from pathlib import Path

REF = "/opt/references/virus/sars_cov_2.fa.gz"
SEED = 20250418
WINDOW_START = 1000
WINDOW_LEN = 1200

N_SEQS = 5
MUT_RATES = [0.00, 0.01, 0.03, 0.05, 0.10]  # distinct per-seq

DATA = Path("/out/data/seqs.fa")
GOLD = Path("/out/gold/identity.tsv")


def mutate(seq: str, rate: float, rng: random.Random) -> str:
    bases = "ACGT"
    out = []
    for b in seq:
        if b in bases and rng.random() < rate:
            alt = rng.choice([x for x in bases if x != b])
            out.append(alt)
        else:
            out.append(b)
    return "".join(out)


def identity(a: str, b: str) -> float:
    matches = 0
    denom = 0
    for ca, cb in zip(a, b):
        if ca == "-" and cb == "-":
            continue
        denom += 1
        if ca == cb:
            matches += 1
    return matches / denom if denom else 0.0


def main() -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    with gzip.open(REF, "rt") as fh:
        fh.readline()  # discard header
        body = "".join(l.rstrip("\n") for l in fh).upper()
    base = body[WINDOW_START: WINDOW_START + WINDOW_LEN].replace("N", "A")

    rng = random.Random(SEED)
    seq_ids = [f"seq_{i + 1}" for i in range(N_SEQS)]
    variants = [mutate(base, r, rng) for r in MUT_RATES]

    with DATA.open("w") as fh:
        for sid, seq in zip(seq_ids, variants):
            fh.write(f">{sid}\n")
            for i in range(0, len(seq), 80):
                fh.write(seq[i:i + 80] + "\n")

    # Align; parse; compute identities; write gold upper triangle.
    aligned = subprocess.check_output(
        ["mafft", "--auto", "--quiet", str(DATA)], text=True
    )
    records: dict[str, str] = {}
    cur = None
    buf: list[str] = []
    for line in aligned.splitlines():
        if line.startswith(">"):
            if cur is not None:
                records[cur] = "".join(buf).upper()
            cur = line[1:].split()[0]
            buf = []
        else:
            buf.append(line.strip())
    if cur is not None:
        records[cur] = "".join(buf).upper()

    with GOLD.open("w") as fh:
        fh.write("seq_a\tseq_b\tidentity\n")
        rows = []
        for i, a in enumerate(seq_ids):
            for b in seq_ids[i + 1:]:
                rows.append((a, b, identity(records[a], records[b])))
        rows.sort(key=lambda r: (r[0], r[1]))
        for a, b, ident in rows:
            fh.write(f"{a}\t{b}\t{ident:.6f}\n")

    print(f"wrote {DATA} ({N_SEQS} seqs, len~{WINDOW_LEN}) and "
          f"{GOLD} ({len(rows)} pairs)")


if __name__ == "__main__":
    main()
