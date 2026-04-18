#!/usr/bin/env python3
"""Grader for seqkit-gc-window (Pattern A, exact diff)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/gc_windows.tsv")
GOLD = Path("/gold/gc_windows.tsv")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")

actual = OUT.read_text()
gold = GOLD.read_text()

if actual != gold:
    a = actual.splitlines()
    g = gold.splitlines()
    if len(a) != len(g):
        fail(f"row count: actual={len(a)} gold={len(g)}")
    for i, (x, y) in enumerate(zip(a, g), start=1):
        if x != y:
            fail(f"row {i} differs\n  actual: {x!r}\n  gold:   {y!r}")
    fail("trailing-newline mismatch")

print(f"ok: {len(actual.splitlines())} rows match gold")
sys.exit(0)
