#!/usr/bin/env python3
"""Grader for gtf-to-bed (Pattern A: byte-identical BED after normalization)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/exons.bed")
GOLD = Path("/gold/exons.bed")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def load(path: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    for lineno, raw in enumerate(path.read_text().splitlines(), 1):
        if not raw:
            continue
        cols = raw.split("\t")
        if len(cols) != 6:
            fail(f"{path} line {lineno}: expected 6 tab-columns, got {len(cols)}")
        rows.append(cols)
    return rows


if not OUT.is_file():
    fail(f"missing {OUT}")

actual = load(OUT)
gold = load(GOLD)

if len(actual) != len(gold):
    fail(f"row count mismatch: actual={len(actual)} gold={len(gold)}")

# Column-type sanity on actual
for i, cols in enumerate(actual, 1):
    try:
        s, e = int(cols[1]), int(cols[2])
    except ValueError:
        fail(f"row {i}: start/end not integer: {cols[1]!r},{cols[2]!r}")
    if s >= e:
        fail(f"row {i}: start {s} >= end {e}")
    if cols[4] != ".":
        fail(f"row {i}: score must be '.', got {cols[4]!r}")
    if cols[5] not in {"+", "-", "."}:
        fail(f"row {i}: strand must be +, -, or .; got {cols[5]!r}")

# Enforce sort order on actual
expected_order = sorted(actual, key=lambda r: (r[0], int(r[1]), int(r[2]), r[3]))
if actual != expected_order:
    fail("rows not sorted by (chrom, start, end, name)")

for i, (a, g) in enumerate(zip(actual, gold), 1):
    if a != g:
        fail(f"row {i} mismatch:\n  actual={a}\n  gold  ={g}")

print(f"ok: {len(actual)} exon rows match gold")
sys.exit(0)
