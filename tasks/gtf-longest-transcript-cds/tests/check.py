#!/usr/bin/env python3
"""Grader for gtf-longest-transcript-cds (Pattern A, exact diff)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/longest_cds.tsv")
GOLD = Path("/gold/longest_cds.tsv")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")

actual = OUT.read_text()
gold = GOLD.read_text()

if actual != gold:
    a_lines = actual.splitlines()
    g_lines = gold.splitlines()
    if len(a_lines) != len(g_lines):
        fail(f"row count: actual={len(a_lines)} gold={len(g_lines)}")
    for i, (a, g) in enumerate(zip(a_lines, g_lines), start=1):
        if a != g:
            fail(f"row {i} differs\n  actual: {a!r}\n  gold:   {g!r}")
    fail("trailing-newline mismatch")

print(f"ok: {len(actual.splitlines())} rows match gold")
sys.exit(0)
