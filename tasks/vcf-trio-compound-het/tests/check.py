#!/usr/bin/env python3
"""Grader for vcf-trio-compound-het."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/compound_hets.tsv")
GOLD = Path("/gold/compound_hets.tsv")
HEADER = "gene\tn_paternal\tn_maternal\tfirst_paternal_pos\tfirst_maternal_pos"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")

actual = OUT.read_text().splitlines()
gold = GOLD.read_text().splitlines()
if not actual or actual[0] != HEADER:
    fail(f"header must be exactly '{HEADER}'")
if actual != gold:
    fail("output differs from gold")

print(f"ok: {len(actual) - 1} compound-het genes")
