#!/usr/bin/env python3
"""Generate a paired-end BAM ready for `samtools markdup`.

Produces a coord-sorted, fixmate-tagged BAM (see samtools markdup docs:
the input must be name-sorted then fixmate'd then coord-sorted before
markdup). Some read pairs share the same 5' position → will be flagged
as duplicates by markdup.

Writes:
  /out/data/reads.bam
  /out/data/reads.bam.bai
  /out/gold/counts.json     {"duplicates": N, "primary_total": M}
"""
from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path

import pysam

REF = "/opt/references/virus/sars_cov_2.fa.gz"
SEED = 20250418
N_UNIQUE_PAIRS = 150
N_DUP_PAIRS = 40
READ_LEN = 80
INSERT = 200

DATA = Path("/out/data/reads.bam")
GOLD = Path("/out/gold/counts.json")


def main() -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)
    fa = pysam.FastaFile(REF)
    rname = fa.references[0]
    reflen = fa.get_reference_length(rname)

    def grab(pos: int) -> str:
        s = fa.fetch(rname, pos, pos + READ_LEN).upper()
        return s.replace("N", "A")

    sam_lines = [
        "@HD\tVN:1.6\tSO:unsorted\n",
        f"@SQ\tSN:{rname}\tLN:{reflen}\n",
        "@PG\tID:bioterm-bench\tPN:bioterm-bench\tVN:0.1\n",
    ]

    def emit_pair(name: str, p1: int, p2: int) -> None:
        seq1 = grab(p1)
        seq2 = grab(p2)
        qual = "I" * READ_LEN
        tlen = p2 + READ_LEN - p1
        sam_lines.append(
            f"{name}\t99\t{rname}\t{p1 + 1}\t60\t{READ_LEN}M\t=\t{p2 + 1}\t{tlen}\t{seq1}\t{qual}\n"
        )
        sam_lines.append(
            f"{name}\t147\t{rname}\t{p2 + 1}\t60\t{READ_LEN}M\t=\t{p1 + 1}\t{-tlen}\t{seq2}\t{qual}\n"
        )

    unique_positions: list[int] = []
    for i in range(N_UNIQUE_PAIRS):
        p1 = rng.randint(0, reflen - INSERT - READ_LEN - 1)
        p2 = p1 + INSERT - READ_LEN
        unique_positions.append(p1)
        emit_pair(f"u_{i:04d}", p1, p2)

    # Duplicate pairs share the same 5' start with some of the
    # unique pairs. This is what samtools markdup detects.
    rng2 = random.Random(SEED + 1)
    for j in range(N_DUP_PAIRS):
        p1 = rng2.choice(unique_positions)
        p2 = p1 + INSERT - READ_LEN
        emit_pair(f"d_{j:04d}", p1, p2)

    sam_path = Path("/tmp/raw.sam")
    sam_path.write_text("".join(sam_lines))

    # Pipeline: name-sort → fixmate (-m adds MC/MQ tags) → coord-sort.
    # Agent then runs markdup on the produced BAM.
    subprocess.check_call([
        "bash", "-c",
        "set -euo pipefail; "
        f"samtools sort -n -O bam {sam_path} "
        "| samtools fixmate -m - - "
        f"| samtools sort -O bam -o {DATA} -"
    ])
    subprocess.check_call(["samtools", "index", str(DATA)])

    # Compute the gold duplicate count using an authoritative markdup run.
    markdup_out = Path("/tmp/markdup.bam")
    subprocess.check_call(
        ["samtools", "markdup", str(DATA), str(markdup_out)]
    )
    r = subprocess.check_output(
        ["samtools", "flagstat", "-O", "json", str(markdup_out)], text=True,
    )
    j = json.loads(r)
    qc = j["QC-passed reads"]
    gold = {
        "duplicates": qc["duplicates"],
        "primary_total": qc["primary"],
    }
    GOLD.write_text(json.dumps(gold, indent=2, sort_keys=True) + "\n")
    print(f"wrote {DATA} and gold duplicates={gold['duplicates']} "
          f"primary_total={gold['primary_total']}")


if __name__ == "__main__":
    main()
