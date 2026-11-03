#!/usr/bin/env python3
"""Grader for vcf-allele-frequency (Pattern C per-row, exact key set)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/af.tsv")
GOLD = Path("/tests/gold/af.tsv")
TOL = 1e-4


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def parse(path: Path) -> list[tuple[str, int, float]]:
    lines = [l.rstrip("\r") for l in path.read_text().splitlines() if l.strip()]
    if not lines or lines[0].split("\t") != ["CHROM", "POS", "AF"]:
        fail(f"{path} header must be 'CHROM\\tPOS\\tAF'")
    rows: list[tuple[str, int, float]] = []
    for i, line in enumerate(lines[1:], 2):
        parts = line.split("\t")
        if len(parts) != 3:
            fail(f"{path} line {i} not 3 columns: {line!r}")
        try:
            pos = int(parts[1])
            af = float(parts[2])
        except ValueError:
            fail(f"{path} line {i} non-numeric: {line!r}")
        rows.append((parts[0], pos, af))
    return rows


if not OUT.is_file():
    fail(f"missing {OUT}")

actual = parse(OUT)
gold = parse(GOLD)

a_dict = {(c, p): af for c, p, af in actual}
g_dict = {(c, p): af for c, p, af in gold}

if set(a_dict) != set(g_dict):
    missing = set(g_dict) - set(a_dict)
    extra = set(a_dict) - set(g_dict)
    fail(f"row-set mismatch: {len(missing)} missing, {len(extra)} extra")

bad = [(k, a_dict[k], g_dict[k]) for k in g_dict if abs(a_dict[k] - g_dict[k]) > TOL]
if bad:
    fail(f"{len(bad)} AF values differ by >{TOL}; first: {bad[:3]}")

print(f"ok: {len(actual)} AF rows within tolerance {TOL}")
sys.exit(0)
