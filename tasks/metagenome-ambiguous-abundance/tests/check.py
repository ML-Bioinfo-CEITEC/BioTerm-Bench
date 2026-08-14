#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path

OUT = Path("/app/output/abundance.tsv")
GOLD = Path("/gold/abundance.tsv")

HEADER = [
    "reference_id",
    "length_bp",
    "unique_reads",
    "ambiguous_weight",
    "weighted_reads",
    "rel_abundance_ppm",
]
TOLS = {"ambiguous_weight": 1e-4, "weighted_reads": 1e-4, "rel_abundance_ppm": 1e-3}


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
    if a_row[0] != g_row[0]:
        fail(f"row {i}: reference_id actual={a_row[0]!r} gold={g_row[0]!r}")
    if a_row[1] != g_row[1] or a_row[2] != g_row[2]:
        fail(f"row {i}: integer columns differ actual={a_row[:3]!r} gold={g_row[:3]!r}")
    for idx, name in ((3, "ambiguous_weight"), (4, "weighted_reads"), (5, "rel_abundance_ppm")):
        try:
            a_val = float(a_row[idx])
            g_val = float(g_row[idx])
        except ValueError:
            fail(f"row {i}: {name} is not numeric")
        if abs(a_val - g_val) > TOLS[name]:
            fail(f"row {i} {name}: actual={a_val} gold={g_val} tol={TOLS[name]}")

print(f"ok: {len(actual) - 1} metagenome abundance rows match gold")
