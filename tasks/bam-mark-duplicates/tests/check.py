#!/usr/bin/env python3
"""Grader for bam-mark-duplicates (Pattern C, tolerance=0)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path("/app/output/counts.json")
GOLD = Path("/tests/gold/counts.json")
REQUIRED = {"duplicates", "primary_total"}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")

try:
    actual = json.loads(OUT.read_text())
except json.JSONDecodeError as exc:
    fail(f"{OUT} is not valid JSON: {exc}")

if not isinstance(actual, dict) or set(actual.keys()) != REQUIRED:
    fail(f"keys {sorted(actual) if isinstance(actual, dict) else 'N/A'} "
         f"!= required {sorted(REQUIRED)}")

gold = json.loads(GOLD.read_text())
for k in sorted(REQUIRED):
    if not isinstance(actual[k], int):
        fail(f"{k} must be an integer, got {type(actual[k]).__name__}")
    if actual[k] != gold[k]:
        fail(f"{k} actual={actual[k]} gold={gold[k]}")

print(f"ok: duplicates={actual['duplicates']} "
      f"primary_total={actual['primary_total']}")
sys.exit(0)
