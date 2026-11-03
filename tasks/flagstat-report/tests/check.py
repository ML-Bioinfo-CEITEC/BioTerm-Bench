#!/usr/bin/env python3
"""Grader for flagstat-report (Pattern A: exact diff after normalize)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/metrics.tsv")
GOLD = Path("/tests/gold/metrics.tsv")

REQUIRED = {"total_reads", "mapped", "properly_paired", "duplicates", "supplementary"}


def parse(path: Path) -> dict[str, str]:
    d: dict[str, str] = {}
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            print(f"FAIL: {path} line {lineno} not exactly 2 tab-columns: {line!r}",
                  file=sys.stderr)
            sys.exit(1)
        d[parts[0]] = parts[1]
    return d


if not OUT.is_file():
    print(f"FAIL: missing {OUT}", file=sys.stderr)
    sys.exit(1)

actual = parse(OUT)
gold = parse(GOLD)

if set(actual.keys()) != REQUIRED:
    print(f"FAIL: metric set mismatch actual={sorted(actual)} expected={sorted(REQUIRED)}",
          file=sys.stderr)
    sys.exit(1)

# Require values to match exactly, and to be integer-formatted.
for k in sorted(REQUIRED):
    if k not in gold:
        print(f"FAIL: gold missing {k} (bug in task data)", file=sys.stderr)
        sys.exit(1)
    if actual[k] != gold[k]:
        print(f"FAIL: {k} actual={actual[k]} gold={gold[k]}", file=sys.stderr)
        sys.exit(1)
    try:
        int(actual[k])
    except ValueError:
        print(f"FAIL: {k} value {actual[k]!r} is not an integer", file=sys.stderr)
        sys.exit(1)

# Enforce alphabetical sort in the output
rows = [l for l in OUT.read_text().splitlines() if l.strip()]
keys = [r.split("\t")[0] for r in rows]
if keys != sorted(keys):
    print(f"FAIL: rows not alphabetically sorted: {keys}", file=sys.stderr)
    sys.exit(1)

print("ok: all 5 metrics match and sorted")
sys.exit(0)
