#!/usr/bin/env python3
"""Grader for bam-splice-junction-support."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

OUT = Path("/app/output/support.tsv")
GOLD = Path("/gold/support.tsv")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def load(path: Path) -> list[list[str]]:
    with path.open() as fh:
        return list(csv.reader(fh, delimiter="\t"))


if not OUT.is_file():
    fail(f"missing {OUT}")

actual_text = OUT.read_text()
gold_text = GOLD.read_text()
if actual_text != gold_text:
    actual = load(OUT)
    gold = load(GOLD)
    if len(actual) != len(gold):
        fail(f"row count mismatch: actual={len(actual)} gold={len(gold)}")
    for idx, (a_row, g_row) in enumerate(zip(actual, gold), start=1):
        if a_row != g_row:
            fail(f"row {idx} differs\n  actual={a_row}\n  gold  ={g_row}")
    fail("trailing-newline mismatch")

rows = load(OUT)
if rows[0] != ["gene_id", "transcript_id", "junction_index", "chrom", "intron_start", "intron_end", "support_reads"]:
    fail("header mismatch")
for idx, row in enumerate(rows[1:], start=2):
    if len(row) != 7:
        fail(f"row {idx} has {len(row)} columns")
    try:
        for col in (2, 4, 5, 6):
            if int(row[col]) < 0:
                fail(f"row {idx} contains negative integer")
    except ValueError as exc:
        fail(f"row {idx} integer parse failed: {exc}")

print(f"ok: {len(rows) - 1} annotated junction rows match gold")
