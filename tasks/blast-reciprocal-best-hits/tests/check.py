#!/usr/bin/env python3
"""Grader for blast-reciprocal-best-hits (Pattern A, exact diff)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/rbh.tsv")
GOLD = Path("/gold/rbh.tsv")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def parse(path: Path) -> list[tuple[str, str]]:
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        f = line.split("\t")
        if len(f) < 2:
            fail(f"bad row in {path}: {line!r}")
        rows.append((f[0], f[1]))
    return rows


if not OUT.is_file():
    fail(f"missing {OUT}")

actual = parse(OUT)
gold = parse(GOLD)

if sorted(actual) != actual:
    fail("actual rows not sorted by a_id asc")
if actual != gold:
    fail(f"rows differ\n  actual: {actual}\n  gold:   {gold}")

print(f"ok: {len(actual)} RBH pairs match gold")
sys.exit(0)
