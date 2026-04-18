#!/usr/bin/env python3
"""Grader for gtf-gene-lengths (Pattern A: exact diff)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/gene_lengths.tsv")
GOLD = Path("/gold/gene_lengths.tsv")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def parse(path: Path) -> tuple[list[str], list[tuple[str, int]]]:
    lines = [l.rstrip("\r") for l in path.read_text().splitlines() if l.strip()]
    if not lines:
        fail(f"{path} is empty")
    header = lines[0].split("\t")
    if header != ["gene_id", "length"]:
        fail(f"{path} header expected ['gene_id','length'], got {header}")
    rows: list[tuple[str, int]] = []
    for i, line in enumerate(lines[1:], 2):
        parts = line.split("\t")
        if len(parts) != 2:
            fail(f"{path} line {i} not 2 columns: {line!r}")
        try:
            rows.append((parts[0], int(parts[1])))
        except ValueError:
            fail(f"{path} line {i} length not an integer: {line!r}")
    return header, rows


if not OUT.is_file():
    fail(f"missing {OUT}")

_, actual = parse(OUT)
_, gold = parse(GOLD)

if [r[0] for r in actual] != sorted(r[0] for r in actual):
    fail("rows are not sorted by gene_id ascending")

if dict(actual) != dict(gold):
    missing = set(dict(gold)) - set(dict(actual))
    extra = set(dict(actual)) - set(dict(gold))
    mismatched = [
        (g, dict(gold)[g], dict(actual)[g])
        for g in set(dict(gold)) & set(dict(actual))
        if dict(gold)[g] != dict(actual)[g]
    ]
    fail(f"{len(missing)} missing, {len(extra)} extra, "
         f"{len(mismatched)} wrong lengths (first: {mismatched[:3]})")

print(f"ok: {len(actual)} genes match gold lengths")
sys.exit(0)
