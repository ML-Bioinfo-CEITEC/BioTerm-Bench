#!/usr/bin/env python3
"""Grader for fasta-rename-headers (Pattern A: exact file diff)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/renamed.fa")
GOLD = Path("/gold/renamed.fa")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")

actual = OUT.read_text()
gold = GOLD.read_text()

# Normalize: strip trailing whitespace per line and any trailing \r
# (agents may produce CRLF on some platforms); otherwise require exact.
def norm(s: str) -> list[str]:
    return [line.rstrip("\r\n").rstrip() for line in s.splitlines() if line.strip()]


a = norm(actual)
g = norm(gold)

if a != g:
    # Report first diff to help debugging but exit nonzero.
    for i, (x, y) in enumerate(zip(a, g)):
        if x != y:
            fail(f"line {i + 1} actual={x!r} gold={y!r}")
    fail(f"length mismatch actual={len(a)} gold={len(g)}")

print(f"ok: renamed.fa matches gold ({len(a)} non-empty lines)")
sys.exit(0)
