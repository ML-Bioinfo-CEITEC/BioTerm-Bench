#!/usr/bin/env python3
"""Generate paired FASTQs with shuffled mates, adapters, and orphans."""
from __future__ import annotations

import gzip
import json
import os
import random
from pathlib import Path

SEED = 20260812
OUT_ROOT = Path(os.environ.get("OUT_ROOT", "/out"))
R1 = OUT_ROOT / "data" / "reads_R1.fastq.gz"
R2 = OUT_ROOT / "data" / "reads_R2.fastq.gz"
GOLD_SUMMARY = OUT_ROOT / "gold" / "summary.json"
GOLD_ORPHANS = OUT_ROOT / "gold" / "orphans.tsv"
ADAPTER = "AGATCGGAAGAGC"


def normalize_id(header: str) -> str:
    token = header.split()[0]
    if token.endswith(("/1", "/2")):
        token = token[:-2]
    return token


def random_seq(rng: random.Random, length: int) -> str:
    return "".join(rng.choices("ACGT", k=length))


def random_qual(rng: random.Random, length: int, base_q: int) -> list[int]:
    vals = []
    for pos in range(length):
        decay = base_q - round(8 * pos / max(length - 1, 1))
        vals.append(max(8, min(40, decay + rng.randint(-2, 2))))
    return vals


def write_fastq(path: Path, records: list[tuple[str, str, list[int]]]) -> None:
    with gzip.open(path, "wt") as fh:
        for rid, seq, quals in records:
            qual_str = "".join(chr(q + 33) for q in quals)
            fh.write(f"@{rid}\n{seq}\n+\n{qual_str}\n")


def main() -> None:
    R1.parent.mkdir(parents=True, exist_ok=True)
    GOLD_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)

    proper_pairs = 260
    orphan_r1_ids = [f"ORPHANR1_{i:03d}" for i in range(18)]
    orphan_r2_ids = [f"ORPHANR2_{i:03d}" for i in range(14)]

    r1_records: list[tuple[str, str, list[int]]] = []
    r2_records: list[tuple[str, str, list[int]]] = []
    q30_num = {"R1": 0, "R2": 0}
    q30_den = {"R1": 0, "R2": 0}
    adapter_pairs = 0
    adapter_both = 0

    for i in range(proper_pairs):
        core_id = f"PAIR_{i:04d}"
        r1_id = f"{core_id}/1" if i % 2 == 0 else f"{core_id} 1:N:0:1"
        r2_id = f"{core_id}/2" if i % 3 == 0 else f"{core_id} 2:N:0:1"

        len1 = rng.randint(72, 110)
        len2 = rng.randint(70, 108)
        seq1 = random_seq(rng, len1)
        seq2 = random_seq(rng, len2)
        has_ad1 = i % 7 == 0 or i % 19 == 0
        has_ad2 = i % 11 == 0 or i % 19 == 0
        if has_ad1:
            start = rng.randint(max(0, len1 - len(ADAPTER) - 12), max(0, len1 - len(ADAPTER)))
            seq1 = seq1[:start] + ADAPTER + seq1[start + len(ADAPTER):]
        if has_ad2:
            start = rng.randint(max(0, len2 - len(ADAPTER) - 10), max(0, len2 - len(ADAPTER)))
            seq2 = seq2[:start] + ADAPTER + seq2[start + len(ADAPTER):]
        qual1 = random_qual(rng, len1, 35)
        qual2 = random_qual(rng, len2, 33)
        r1_records.append((r1_id, seq1, qual1))
        r2_records.append((r2_id, seq2, qual2))
        q30_num["R1"] += sum(1 for q in qual1 if q >= 30)
        q30_den["R1"] += len(qual1)
        q30_num["R2"] += sum(1 for q in qual2 if q >= 30)
        q30_den["R2"] += len(qual2)
        if has_ad1 or has_ad2:
            adapter_pairs += 1
        if has_ad1 and has_ad2:
            adapter_both += 1

    for rid in orphan_r1_ids:
        length = rng.randint(65, 95)
        r1_records.append((f"{rid}/1", random_seq(rng, length), random_qual(rng, length, 31)))
    for rid in orphan_r2_ids:
        length = rng.randint(65, 95)
        r2_records.append((f"{rid}/2", random_seq(rng, length), random_qual(rng, length, 30)))

    rng.shuffle(r1_records)
    rng.shuffle(r2_records)
    write_fastq(R1, r1_records)
    write_fastq(R2, r2_records)

    orphan_rows = ["read_id\tpresent_in"]
    for rid in sorted(orphan_r1_ids):
        orphan_rows.append(f"{rid}\tR1")
    for rid in sorted(orphan_r2_ids):
        orphan_rows.append(f"{rid}\tR2")

    summary = {
        "adapter_pairs": adapter_pairs,
        "adapter_pairs_both_mates": adapter_both,
        "orphan_r1": len(orphan_r1_ids),
        "orphan_r2": len(orphan_r2_ids),
        "proper_pairs": proper_pairs,
        "q30_frac_r1": round(q30_num["R1"] / q30_den["R1"], 4),
        "q30_frac_r2": round(q30_num["R2"] / q30_den["R2"], 4),
        "total_r1": len(r1_records),
        "total_r2": len(r2_records),
    }
    GOLD_SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    GOLD_ORPHANS.write_text("\n".join(orphan_rows) + "\n")
    print(f"wrote {R1}, {R2}, {GOLD_SUMMARY}, {GOLD_ORPHANS}")


if __name__ == "__main__":
    main()
