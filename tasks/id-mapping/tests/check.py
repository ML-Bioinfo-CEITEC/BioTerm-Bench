#!/usr/bin/env python3
"""Grader for id-mapping (Pattern A: exact TSV diff)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/mapping.tsv")
GOLD = Path("/gold/mapping.tsv")

EXPECTED_HEADER = ["query_symbol", "resolved_symbol", "ensembl_gene_id", "status"]
VALID_STATUSES = {"exact", "alias", "not_found"}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")

actual_lines = OUT.read_text().splitlines()
gold_lines = GOLD.read_text().splitlines()

if len(actual_lines) < 1:
    fail("output is empty")

actual_header = actual_lines[0].split("\t")
if actual_header != EXPECTED_HEADER:
    fail(f"header mismatch: got {actual_header}, expected {EXPECTED_HEADER}")

actual_rows = [ln.split("\t") for ln in actual_lines[1:]]
for i, r in enumerate(actual_rows, 2):
    if len(r) != 4:
        fail(f"line {i}: expected 4 tab-separated columns, got {len(r)}")
    if r[3] not in VALID_STATUSES:
        fail(f"line {i}: invalid status '{r[3]}'")
    if r[3] == "not_found":
        if r[1] != "" or r[2] != "":
            fail(f"line {i}: not_found rows must have empty resolved_symbol "
                 f"and ensembl_gene_id, got {r}")
    else:
        if not r[1] or not r[2]:
            fail(f"line {i}: {r[3]} row has empty resolved_symbol or "
                 f"ensembl_gene_id: {r}")

qsyms = [r[0] for r in actual_rows]
if qsyms != sorted(qsyms):
    fail("rows are not sorted ASCII-ascending by query_symbol")

if actual_lines != gold_lines:
    diff_at = next(
        (i for i, (a, g) in enumerate(zip(actual_lines, gold_lines)) if a != g),
        min(len(actual_lines), len(gold_lines)),
    )
    fail(f"output differs from gold at line {diff_at + 1}:\n"
         f"  actual: {actual_lines[diff_at] if diff_at < len(actual_lines) else '<EOF>'}\n"
         f"  gold:   {gold_lines[diff_at] if diff_at < len(gold_lines) else '<EOF>'}")

print(f"ok: {len(actual_rows)} rows mapped, exact match against gold")
sys.exit(0)
