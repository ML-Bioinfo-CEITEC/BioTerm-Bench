#!/usr/bin/env python3
"""Grader for vcf-region-variant-density (Pattern C)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/density.tsv")
GOLD = Path("/tests/gold/density.tsv")
TOL = 1e-4
HEADER = "chrom\tstart\tend\tn_snv\tn_indel\tdensity_per_kb"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")

actual = OUT.read_text().splitlines()
gold = GOLD.read_text().splitlines()

if not actual or actual[0] != HEADER:
    fail(f"header must be exactly '{HEADER}'; got '{actual[0] if actual else ''}'")
if len(actual) != len(gold):
    fail(f"row count mismatch: actual={len(actual)-1} gold={len(gold)-1}")

for i, (a_line, g_line) in enumerate(zip(actual[1:], gold[1:]), start=2):
    a = a_line.split("\t")
    g = g_line.split("\t")
    if len(a) != 6:
        fail(f"row {i}: need 6 columns, got {len(a)}")
    if a[0] != g[0]:
        fail(f"row {i}: chrom actual='{a[0]}' gold='{g[0]}'")
    try:
        a_ints = (int(a[1]), int(a[2]), int(a[3]), int(a[4]))
    except ValueError:
        fail(f"row {i}: start/end/n_snv/n_indel must be int")
    g_ints = (int(g[1]), int(g[2]), int(g[3]), int(g[4]))
    if a_ints != g_ints:
        fail(f"row {i} {a[0]}: ints actual={a_ints} gold={g_ints}")
    try:
        a_d = float(a[5])
    except ValueError:
        fail(f"row {i}: density_per_kb not float")
    g_d = float(g[5])
    if abs(a_d - g_d) > TOL:
        fail(f"row {i} {a[0]}: density actual={a_d} gold={g_d} tol={TOL}")

print(f"ok: {len(actual)-1} intervals match")
sys.exit(0)
