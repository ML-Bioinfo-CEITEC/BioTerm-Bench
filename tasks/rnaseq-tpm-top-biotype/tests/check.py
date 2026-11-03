#!/usr/bin/env python3
"""Grader for rnaseq-tpm-top-biotype (Pattern C, mixed exact + float)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/top_biotype.tsv")
GOLD = Path("/tests/gold/top_biotype.tsv")
TOL = 1e-3
HEADER = "gene_id\tgene_name\tmax_tpm"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")

actual = OUT.read_text().splitlines()
gold = GOLD.read_text().splitlines()

if not actual or actual[0] != HEADER:
    fail(f"header must be exactly '{HEADER}'")
if len(actual) != len(gold):
    fail(f"row count mismatch: actual={len(actual)-1} gold={len(gold)-1}")

for i, (a_line, g_line) in enumerate(zip(actual[1:], gold[1:]), start=2):
    a = a_line.split("\t")
    g = g_line.split("\t")
    if len(a) != 3:
        fail(f"row {i}: need 3 columns")
    if a[0] != g[0]:
        fail(f"row {i}: gene_id actual='{a[0]}' gold='{g[0]}'")
    if a[1] != g[1]:
        fail(f"row {i} {a[0]}: gene_name actual='{a[1]}' gold='{g[1]}'")
    try:
        a_v = float(a[2])
    except ValueError:
        fail(f"row {i}: max_tpm not float")
    g_v = float(g[2])
    if abs(a_v - g_v) > TOL:
        fail(f"row {i} {a[0]}: max_tpm actual={a_v} gold={g_v} tol={TOL}")

print(f"ok: top-{len(actual)-1} protein_coding genes match")
sys.exit(0)
