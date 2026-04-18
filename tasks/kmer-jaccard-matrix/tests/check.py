#!/usr/bin/env python3
"""Grader for kmer-jaccard-matrix (Pattern C; per-row tolerance on jaccard)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/jaccard.tsv")
GOLD = Path("/gold/jaccard.tsv")
TOL = 1e-5


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def parse(path: Path):
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        f = line.split("\t")
        if len(f) != 3:
            fail(f"bad row {line!r} in {path}")
        rows.append((f[0], f[1], float(f[2])))
    return rows


if not OUT.is_file():
    fail(f"missing {OUT}")

actual = parse(OUT)
gold = parse(GOLD)

if len(actual) != len(gold):
    fail(f"row count: actual={len(actual)} gold={len(gold)}")

actual_pairs = [(a, b) for a, b, _ in actual]
gold_pairs = [(a, b) for a, b, _ in gold]
if actual_pairs != gold_pairs:
    fail(f"pair order differs\n  actual: {actual_pairs}\n  gold:   {gold_pairs}")

for i, ((a, b, x), (_, _, y)) in enumerate(zip(actual, gold), start=1):
    if abs(x - y) > TOL:
        fail(f"row {i} ({a},{b}): actual={x} gold={y} tol={TOL}")

print(f"ok: {len(actual)} jaccard rows within tolerance")
sys.exit(0)
