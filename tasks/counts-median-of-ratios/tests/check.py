#!/usr/bin/env python3
"""Grader for counts-median-of-ratios (Pattern C, abs tol=1e-4)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/size_factors.tsv")
GOLD = Path("/gold/size_factors.tsv")
HEADER = ["sample", "size_factor"]
TOL = 1e-4


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def parse(path: Path):
    lines = [l for l in path.read_text().splitlines() if l.strip()]
    if not lines:
        fail(f"{path} empty")
    rows = [l.split("\t") for l in lines]
    if rows[0] != HEADER:
        fail(f"{path} header mismatch: {rows[0]}")
    return rows[1:]


if not OUT.is_file():
    fail(f"missing {OUT}")

actual = parse(OUT)
gold = parse(GOLD)
if len(actual) != len(gold):
    fail(f"row count: actual={len(actual)} gold={len(gold)}")

for i, (a, g) in enumerate(zip(actual, gold), start=1):
    if a[0] != g[0]:
        fail(f"row {i} sample: actual={a[0]} gold={g[0]}")
    try:
        x = float(a[1]); y = float(g[1])
    except ValueError:
        fail(f"row {i} non-numeric size_factor: {a[1]!r}")
    if abs(x - y) > TOL:
        fail(f"row {i} ({a[0]}): actual={x} gold={y} tol={TOL}")

print(f"ok: {len(actual)} size factors match gold")
sys.exit(0)
