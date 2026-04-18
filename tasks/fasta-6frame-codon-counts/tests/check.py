#!/usr/bin/env python3
"""Grader for fasta-6frame-codon-counts (Pattern A, exact diff)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/codon_counts.tsv")
GOLD = Path("/gold/codon_counts.tsv")


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
    if len(a_lines) != 64:
        fail(f"expected 64 lines, got {len(a_lines)}")
    for i, (a, g) in enumerate(zip(a_lines, g_lines), start=1):
        if a != g:
            fail(f"line {i} differs\n  actual: {a!r}\n  gold:   {g!r}")
    fail("trailing-newline / extra-line mismatch")

print("ok: 64 codon counts match gold")
sys.exit(0)
