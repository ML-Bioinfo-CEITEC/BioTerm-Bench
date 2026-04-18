#!/usr/bin/env python3
"""Grader for counts-to-deg-ttest (Pattern C, per-cell tolerance)."""
from __future__ import annotations

import math
import sys
from pathlib import Path

OUT = Path("/app/output/top_deg.tsv")
GOLD = Path("/gold/top_deg.tsv")
HEADER = ["gene_id", "t_stat", "p_value", "mean_cpm_ctrl", "mean_cpm_trt"]


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def parse(path: Path):
    rows = [line.split("\t") for line in path.read_text().splitlines() if line.strip()]
    if not rows or rows[0] != HEADER:
        fail(f"{path} header mismatch: {rows[0] if rows else None}")
    return rows[1:]


if not OUT.is_file():
    fail(f"missing {OUT}")

actual = parse(OUT)
gold = parse(GOLD)

if len(actual) != len(gold) or len(actual) != 20:
    fail(f"row count: actual={len(actual)} gold={len(gold)} (expected 20)")

for i, (a, g) in enumerate(zip(actual, gold), start=1):
    if a[0] != g[0]:
        fail(f"row {i} gene_id: actual={a[0]} gold={g[0]}")
    for ci, col in enumerate(HEADER[1:], start=1):
        try:
            x = float(a[ci]); y = float(g[ci])
        except ValueError:
            fail(f"row {i} col {col} non-numeric: actual={a[ci]!r}")
        if not math.isclose(x, y, rel_tol=1e-4, abs_tol=1e-4):
            fail(f"row {i} {col}: actual={x} gold={y}")

print("ok: 20 DEG rows match gold within tolerance")
sys.exit(0)
