#!/usr/bin/env python3
"""Grader for fastq-per-base-quality (Pattern C)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/per_base_quality.tsv")
GOLD = Path("/tests/gold/per_base_quality.tsv")
TOL = 1e-3
HEADER = "pos\tn\tmean_q\tmedian_q"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")

actual = OUT.read_text().splitlines()
gold = GOLD.read_text().splitlines()

if not actual or actual[0] != HEADER:
    fail(f"header must be exactly '{HEADER}'")
if len(actual) != len(gold):
    fail(f"row count mismatch: actual={len(actual)-1} gold={len(gold)-1}")

for i, (a_line, g_line) in enumerate(zip(actual[1:], gold[1:]), start=2):
    a = a_line.split("\t")
    g = g_line.split("\t")
    if len(a) != 4:
        fail(f"row {i}: need 4 columns")
    try:
        a_pos, a_n = int(a[0]), int(a[1])
    except ValueError:
        fail(f"row {i}: pos/n must be int")
    g_pos, g_n = int(g[0]), int(g[1])
    if a_pos != g_pos:
        fail(f"row {i}: pos actual={a_pos} gold={g_pos}")
    if a_n != g_n:
        fail(f"row {i} pos={a_pos}: n actual={a_n} gold={g_n}")
    for col, name in enumerate(("mean_q", "median_q"), start=2):
        try:
            a_v = float(a[col])
        except ValueError:
            fail(f"row {i}: {name} not float: {a[col]!r}")
        g_v = float(g[col])
        if abs(a_v - g_v) > TOL:
            fail(f"row {i} pos={a_pos}: {name} actual={a_v} gold={g_v} tol={TOL}")

print(f"ok: {len(actual)-1} positions within tolerance {TOL}")
sys.exit(0)
