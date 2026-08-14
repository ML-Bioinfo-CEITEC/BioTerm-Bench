#!/usr/bin/env python3
"""Grader for gtf-reconstruct-translate."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

OUT = Path("/app/output/proteins.tsv")
GOLD = Path("/gold/proteins.tsv")


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
if rows[0] != ["transcript_id", "gene_id", "strand", "cds_length", "peptide_length", "peptide"]:
    fail("header mismatch")
for idx, row in enumerate(rows[1:], start=2):
    if len(row) != 6:
        fail(f"row {idx} has {len(row)} columns")
    try:
        cds_len = int(row[3])
        pep_len = int(row[4])
    except ValueError as exc:
        fail(f"row {idx} integer parse failed: {exc}")
    if cds_len != pep_len * 3:
        fail(f"row {idx} cds_length={cds_len} is not 3*peptide_length={pep_len}")
    if "*" in row[5]:
        fail(f"row {idx} peptide contains stop codon")

print(f"ok: {len(rows) - 1} translated CDS rows match gold")
