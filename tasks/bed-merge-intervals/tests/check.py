#!/usr/bin/env python3
"""Grader for bed-merge-intervals (Pattern A)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/merged.bed")
GOLD = Path("/gold/merged.bed")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def parse(path: Path) -> list[tuple[str, int, int]]:
    rows: list[tuple[str, int, int]] = []
    for lineno, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.rstrip("\r")
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            fail(f"{path} line {lineno} not 3 tab-columns: {line!r}")
        try:
            s = int(parts[1])
            e = int(parts[2])
        except ValueError:
            fail(f"{path} line {lineno} non-integer coords: {line!r}")
        if s < 0 or e <= s:
            fail(f"{path} line {lineno} invalid half-open interval: {line!r}")
        rows.append((parts[0], s, e))
    return rows


if not OUT.is_file():
    fail(f"missing {OUT}")

actual = parse(OUT)
gold = parse(GOLD)

# Require the output to be sorted the way we asked.
if sorted(actual, key=lambda r: (r[0], r[1])) != actual:
    fail("output is not sorted by (chrom asc, start asc)")

if actual != gold:
    # Report a small diff for debugging.
    diff_a = set(actual) - set(gold)
    diff_g = set(gold) - set(actual)
    fail(f"mismatch: {len(diff_a)} extra, {len(diff_g)} missing "
         f"(actual={len(actual)} gold={len(gold)})")

print(f"ok: merged.bed matches gold ({len(actual)} rows)")
sys.exit(0)
