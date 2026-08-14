#!/usr/bin/env python3
"""Generate protein queries and gold best-hit TSV for blast-best-hit.

Pulls 5 distinct entries out of the kinome BLAST database, mutates
each query by introducing ~3% substitutions so they are obviously
not identical to their database entry but still BLAST to them as the
top hit.

Writes:
  /out/data/queries.fasta
  /out/gold/best_hits.tsv
"""
from __future__ import annotations

import random
import subprocess
from pathlib import Path

DB = "/opt/references/blast_db/kinome"
DATA_FASTA = Path("/out/data/queries.fasta")
GOLD = Path("/out/gold/best_hits.tsv")

SEED = 20250418
N_QUERIES = 5
MUT_RATE = 0.03
AA = "ACDEFGHIKLMNPQRSTVWY"


def fetch_first_n_entries(n: int) -> list[tuple[str, str]]:
    """Return [(accession, sequence)] for the first n entries from the DB."""
    out = subprocess.check_output(
        ["blastdbcmd", "-db", DB, "-entry", "all"], text=True
    )
    records: list[tuple[str, str]] = []
    current_id = None
    current_seq: list[str] = []
    for line in out.splitlines():
        if line.startswith(">"):
            if current_id is not None:
                records.append((current_id, "".join(current_seq)))
            # header looks like ">sp|P12345|GENE_HUMAN Description..."
            header = line[1:].split()[0]
            parts = header.split("|")
            acc = parts[1] if len(parts) >= 2 else header
            current_id = acc
            current_seq = []
        else:
            current_seq.append(line.strip())
        if len(records) >= n and current_id is not None:
            # keep reading until we have len(records)+1 then break
            pass
    if current_id is not None and len(records) < n + 1:
        records.append((current_id, "".join(current_seq)))
    return records[:n]


def mutate(seq: str, rng: random.Random) -> str:
    out = []
    for aa in seq:
        if aa in AA and rng.random() < MUT_RATE:
            out.append(rng.choice([x for x in AA if x != aa]))
        else:
            out.append(aa)
    return "".join(out)


def main() -> None:
    rng = random.Random(SEED)
    DATA_FASTA.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    records = fetch_first_n_entries(N_QUERIES)
    # Sort by accession for determinism
    records.sort(key=lambda r: r[0])

    with DATA_FASTA.open("w") as fh:
        for i, (acc, seq) in enumerate(records, 1):
            qid = f"query_{i:02d}"
            mseq = mutate(seq, rng)
            fh.write(f">{qid}\n")
            # Wrap at 60
            for k in range(0, len(mseq), 60):
                fh.write(mseq[k : k + 60] + "\n")

    # Generate gold by running blastp on the same input
    tmp = Path("/tmp/raw.tsv")
    subprocess.check_call(
        f"blastp -query {DATA_FASTA} -db {DB} "
        "-outfmt '6 qseqid sseqid bitscore evalue' "
        f"-max_target_seqs 1 -max_hsps 1 -num_threads 2 > {tmp}",
        shell=True,
    )
    best: dict[str, tuple[float, float, str]] = {}
    with tmp.open() as fh:
        for line in fh:
            qid, sseqid, bitscore, evalue = line.rstrip("\n").split("\t")
            cand = (float(bitscore), -float(evalue), sseqid)
            prev = best.get(qid)
            if prev is None or cand > (prev[0], -prev[1], prev[2]):
                best[qid] = (float(bitscore), float(evalue), sseqid)

    query_ids = [f"query_{i:02d}" for i in range(1, N_QUERIES + 1)]
    with GOLD.open("w") as fh:
        for q in sorted(query_ids):
            sseqid = best[q][2].rstrip("|")
            fh.write(f"{q}\t{sseqid}\n")
    print(f"wrote {DATA_FASTA} and {GOLD}")
    for q in sorted(query_ids):
        print(f"  {q}\t{best[q][2]}")


if __name__ == "__main__":
    main()
