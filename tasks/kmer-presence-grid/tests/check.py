#!/usr/bin/env python3
"""Grader for kmer-presence-grid (Pattern A)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/presence.tsv")
GOLD = Path("/gold/presence.tsv")
KMERS = Path("/app/data/kmers.txt")
GENOMES = Path("/app/data/genomes")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def load(path: Path) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            fail(f"{path} line {lineno}: expected 3 columns, got {len(parts)}")
        rows.append((parts[0], parts[1], parts[2]))
    return rows


if not OUT.is_file():
    fail(f"missing {OUT}")

actual = load(OUT)
gold = load(GOLD)

# Combinatorial expectation: every (genome, kmer) pair appears once
kmers = sorted(k.strip() for k in KMERS.read_text().splitlines() if k.strip())
genomes = sorted(p.stem for p in GENOMES.glob("*.fa"))
expected_keys = {(g, k) for g in genomes for k in kmers}
actual_keys = {(g, k) for g, k, _ in actual}
if actual_keys != expected_keys:
    extra = actual_keys - expected_keys
    missing = expected_keys - actual_keys
    fail(f"key set mismatch: extra={sorted(extra)[:5]} missing={sorted(missing)[:5]}")

# Present column constraint
for g, k, p in actual:
    if p not in {"0", "1"}:
        fail(f"present column must be '0' or '1'; got {p!r} for ({g},{k})")

# Sort check
if actual != sorted(actual, key=lambda r: (r[0], r[1])):
    fail("rows not sorted by (genome_id, kmer)")

# Compare against gold
if actual != gold:
    # Pinpoint first mismatch
    for i, (a, gl) in enumerate(zip(actual, gold)):
        if a != gl:
            fail(f"row {i+1} actual={a} gold={gl}")
    fail(f"row count mismatch actual={len(actual)} gold={len(gold)}")

print(f"ok: {len(actual)} presence rows match gold")
sys.exit(0)
