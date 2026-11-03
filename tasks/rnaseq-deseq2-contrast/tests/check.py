#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

OUT = Path("/app/output/de_hits.tsv")
GOLD = Path("/tests/gold/de_hits.tsv")

HEADER = ["gene_id", "gene_name", "baseMean", "log2FoldChange", "padj"]
TOL_BASE = 1e-3
TOL_OTHER = 1e-4


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")

with OUT.open() as fh:
    actual = list(csv.reader(fh, delimiter="\t"))
with GOLD.open() as fh:
    gold = list(csv.reader(fh, delimiter="\t"))

if not actual or actual[0] != HEADER:
    fail(f"header must be exactly {HEADER}")
if len(actual) != len(gold):
    fail(f"row count mismatch: actual={len(actual) - 1} gold={len(gold) - 1}")

for i, (a_row, g_row) in enumerate(zip(actual[1:], gold[1:]), start=2):
    if a_row[:2] != g_row[:2]:
        fail(f"row {i}: actual keys={a_row[:2]!r} gold keys={g_row[:2]!r}")
    if len(a_row) != 5:
        fail(f"row {i}: expected 5 columns")
    vals = [(a_row[2], g_row[2], TOL_BASE, "baseMean"),
            (a_row[3], g_row[3], TOL_OTHER, "log2FoldChange"),
            (a_row[4], g_row[4], TOL_OTHER, "padj")]
    for a_val, g_val, tol, name in vals:
        try:
            a_num = float(a_val)
            g_num = float(g_val)
        except ValueError:
            fail(f"row {i}: {name} is not numeric")
        if abs(a_num - g_num) > tol:
            fail(
                f"row {i} {a_row[0]} {name}: actual={a_num} gold={g_num} tol={tol}"
            )

print(f"ok: top {len(actual) - 1} DESeq2 hits match gold")
