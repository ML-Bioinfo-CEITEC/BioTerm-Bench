#!/usr/bin/env python3
"""Generate a small FASTA + mapping TSV + gold renamed FASTA.

Deterministic, seeded. Writes:
  /out/data/in.fa
  /out/data/map.tsv
  /out/gold/renamed.fa
"""
from __future__ import annotations

import random
from pathlib import Path

SEED = 20250418
N_SEQS = 8
SEQ_LEN = 120          # bases per sequence
LINE_WIDTH = 60        # FASTA wrap width

DATA_DIR = Path("/out/data")
GOLD_DIR = Path("/out/gold")


def wrap(s: str, w: int = LINE_WIDTH) -> str:
    return "\n".join(s[i:i + w] for i in range(0, len(s), w))


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)
    bases = "ACGT"

    records = []
    for i in range(N_SEQS):
        old_id = f"contig_{i:03d}"
        # Pad description with something resembling a real FASTA header.
        desc = f" length={SEQ_LEN} assembly=bioterm_v1"
        seq = "".join(rng.choice(bases) for _ in range(SEQ_LEN))
        records.append((old_id, desc, seq))

    # Map 6 of the 8 headers; leave the last 2 unmapped to test the
    # "keep header if not in map" rule.
    mapping: list[tuple[str, str]] = []
    for i, (old, _desc, _seq) in enumerate(records[:6]):
        new = f"gene_{chr(ord('A') + i)}"
        mapping.append((old, new))

    with (DATA_DIR / "in.fa").open("w") as fh:
        for old, desc, seq in records:
            fh.write(f">{old}{desc}\n")
            fh.write(wrap(seq) + "\n")

    with (DATA_DIR / "map.tsv").open("w") as fh:
        fh.write("old_id\tnew_id\n")
        for old, new in mapping:
            fh.write(f"{old}\t{new}\n")

    map_dict = dict(mapping)
    with (GOLD_DIR / "renamed.fa").open("w") as fh:
        for old, _desc, seq in records:
            new_id = map_dict.get(old, old)
            # By spec we drop the description (everything after the id
            # in the original header) and keep only the chosen id.
            fh.write(f">{new_id}\n")
            fh.write(wrap(seq) + "\n")

    print(f"wrote {DATA_DIR}/in.fa ({N_SEQS} seqs), "
          f"{DATA_DIR}/map.tsv ({len(mapping)} rows), "
          f"{GOLD_DIR}/renamed.fa")


if __name__ == "__main__":
    main()
