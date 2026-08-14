#!/usr/bin/env python3
"""Grader for vcf-diploid-consensus."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/consensus.fa")
GOLD = Path("/gold/consensus.fa")


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
        fail(f"line count mismatch: actual={len(a_lines)} gold={len(g_lines)}")
    for idx, (a_line, g_line) in enumerate(zip(a_lines, g_lines), start=1):
        if a_line != g_line:
            fail(f"line {idx} differs\n  actual: {a_line!r}\n  gold:   {g_line!r}")
    fail("trailing-newline mismatch")

headers = [line for line in actual.splitlines() if line.startswith(">")]
expected = [">chrVC1|hap1", ">chrVC1|hap2", ">chrVC2|hap1", ">chrVC2|hap2"]
if headers != expected:
    fail(f"headers mismatch: actual={headers} expected={expected}")

print("ok: diploid consensus FASTA matches gold")
