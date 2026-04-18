#!/usr/bin/env python3
"""Generate a FASTQ + adapter-count task.

Deterministic: ~1000 reads; a fraction have an Illumina-like adapter
substring injected at a random position inside the read.

Writes:
  /out/data/reads.fastq.gz
  /out/data/adapter.txt         single line with the adapter sequence
  /out/gold/counts.json         {"total_reads", "adapter_reads", "adapter_seq"}
"""
from __future__ import annotations

import gzip
import json
import random
from pathlib import Path

SEED = 20250418
N_READS = 1000
READ_LEN = 100
ADAPTER = "AGATCGGAAGAGC"   # first 13 bp of TruSeq Read1 adapter
ADAPTER_FRAC = 0.30

DATA_FQ = Path("/out/data/reads.fastq.gz")
DATA_AD = Path("/out/data/adapter.txt")
GOLD = Path("/out/gold/counts.json")


def main() -> None:
    for p in (DATA_FQ, DATA_AD, GOLD):
        p.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)
    bases = "ACGT"
    n_adapter = 0

    with gzip.open(DATA_FQ, "wt") as fh:
        for i in range(N_READS):
            seq = [rng.choice(bases) for _ in range(READ_LEN)]
            has = rng.random() < ADAPTER_FRAC
            if has:
                # Overwrite a random window with the adapter. Ensure it fits.
                pos = rng.randint(0, READ_LEN - len(ADAPTER))
                for j, b in enumerate(ADAPTER):
                    seq[pos + j] = b
                n_adapter += 1
            s = "".join(seq)
            q = "I" * READ_LEN
            fh.write(f"@r{i:05d}\n{s}\n+\n{q}\n")

    DATA_AD.write_text(ADAPTER + "\n")

    GOLD.write_text(json.dumps({
        "total_reads": N_READS,
        "adapter_reads": n_adapter,
        "adapter_seq": ADAPTER,
    }, indent=2, sort_keys=True) + "\n")

    print(f"wrote {N_READS} reads ({n_adapter} with adapter) -> {DATA_FQ}, "
          f"gold={GOLD}")


if __name__ == "__main__":
    main()
