#!/usr/bin/env python3
"""Grader for ortholog-rbh-clusters (Pattern A)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/clusters.tsv")
GOLD = Path("/tests/gold/clusters.tsv")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail("missing /app/output/clusters.tsv")


def load(path: Path) -> list[tuple[str, str, str]]:
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            fail(f"bad row in {path}: {line!r}")
        rows.append(tuple(parts))
    return rows


actual = load(OUT)
gold = load(GOLD)

if actual != sorted(actual):
    fail("clusters are not lexicographically sorted")

used = set()
for row in actual:
    for protein in row:
        if protein in used:
            fail(f"protein reused across clusters: {protein}")
        used.add(protein)

if actual != gold:
    fail(f"clusters differ from gold\nactual={actual}\ngold={gold}")

print("ok: RBH clusters match gold exactly")
