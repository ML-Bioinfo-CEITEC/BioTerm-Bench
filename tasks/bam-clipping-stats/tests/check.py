#!/usr/bin/env python3
"""Grader for bam-clipping-stats (Pattern C, tolerance=1e-3 on floats)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path("/app/output/stats.json")
GOLD = Path("/tests/gold/stats.json")
INTS = ("n_primary_mapped", "n_with_any_clip")
FLOATS = ("mean_total_clip", "p90_total_clip")
REQUIRED = set(INTS) | set(FLOATS)
TOL = 1e-3


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")

try:
    actual = json.loads(OUT.read_text())
except json.JSONDecodeError as exc:
    fail(f"{OUT} is not valid JSON: {exc}")

if not isinstance(actual, dict) or set(actual) != REQUIRED:
    fail(f"keys {sorted(actual) if isinstance(actual, dict) else '?'} "
         f"!= required {sorted(REQUIRED)}")

gold = json.loads(GOLD.read_text())

for k in INTS:
    if not isinstance(actual[k], int):
        fail(f"{k} must be int, got {type(actual[k]).__name__}")
    if actual[k] != gold[k]:
        fail(f"{k}: actual={actual[k]} gold={gold[k]}")

for k in FLOATS:
    if not isinstance(actual[k], (int, float)):
        fail(f"{k} must be numeric, got {type(actual[k]).__name__}")
    if abs(float(actual[k]) - float(gold[k])) > TOL:
        fail(f"{k}: actual={actual[k]} gold={gold[k]} tol={TOL}")

print(f"ok: {actual}")
sys.exit(0)
