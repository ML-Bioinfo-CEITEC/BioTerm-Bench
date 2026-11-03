#!/usr/bin/env python3
"""Grader for vcf-to-tsv (Pattern A: byte-identical TSV)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/variants.tsv")
GOLD = Path("/tests/gold/variants.tsv")
HEADER = ["chrom", "pos", "ref", "alt", "qual", "dp", "gt", "vtype"]
VALID_VTYPE = {"snp", "indel"}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")

actual = OUT.read_text().splitlines()
gold = GOLD.read_text().splitlines()

if not actual:
    fail("output is empty")
if actual[0].split("\t") != HEADER:
    fail(f"header mismatch: got {actual[0].split(chr(9))}, want {HEADER}")

for i, line in enumerate(actual[1:], start=2):
    cols = line.split("\t")
    if len(cols) != 8:
        fail(f"line {i}: expected 8 tab-columns, got {len(cols)}")
    try:
        int(cols[1])
    except ValueError:
        fail(f"line {i}: pos '{cols[1]}' not integer")
    if cols[7] not in VALID_VTYPE:
        fail(f"line {i}: vtype must be snp|indel, got {cols[7]!r}")

if actual != gold:
    diff_at = next(
        (i for i, (a, g) in enumerate(zip(actual, gold)) if a != g),
        min(len(actual), len(gold)),
    )
    fail(f"output differs from gold at line {diff_at + 1}:\n"
         f"  actual: {actual[diff_at] if diff_at < len(actual) else '<EOF>'}\n"
         f"  gold:   {gold[diff_at] if diff_at < len(gold) else '<EOF>'}")

print(f"ok: {len(actual) - 1} VCF records exported to TSV, match gold")
sys.exit(0)
