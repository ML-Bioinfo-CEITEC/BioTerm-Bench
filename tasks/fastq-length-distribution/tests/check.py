#!/usr/bin/env python3
"""Grader for fastq-length-distribution (Pattern A)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/lengths.tsv")
GOLD = Path("/gold/lengths.tsv")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def parse(path: Path) -> list[tuple[int, int]]:
    rows: list[tuple[int, int]] = []
    lines = [l.rstrip("\r") for l in path.read_text().splitlines() if l.strip()]
    if not lines or lines[0].split("\t") != ["length", "count"]:
        fail(f"{path} must start with header row 'length\\tcount'")
    for i, line in enumerate(lines[1:], 2):
        parts = line.split("\t")
        if len(parts) != 2:
            fail(f"{path} line {i} not 2 columns: {line!r}")
        try:
            rows.append((int(parts[0]), int(parts[1])))
        except ValueError:
            fail(f"{path} line {i} non-integer: {line!r}")
    return rows


if not OUT.is_file():
    fail(f"missing {OUT}")

actual = parse(OUT)
gold = parse(GOLD)

lengths = [r[0] for r in actual]
if lengths != sorted(lengths):
    fail("rows not sorted by length ascending")
if len(set(lengths)) != len(lengths):
    fail("duplicate length rows")

if dict(actual) != dict(gold):
    diff = [(L, dict(actual).get(L), dict(gold).get(L))
            for L in sorted(set(dict(actual)) | set(dict(gold)))
            if dict(actual).get(L) != dict(gold).get(L)]
    fail(f"rows differ from gold; first few: {diff[:4]}")

print(f"ok: length distribution matches gold ({len(actual)} bins, "
      f"total={sum(c for _, c in actual)})")
sys.exit(0)
