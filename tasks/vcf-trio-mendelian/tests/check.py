#!/usr/bin/env python3
"""Grader for vcf-trio-mendelian (Pattern C)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path("/app/output/summary.json")
GOLD = Path("/gold/summary.json")
INTS = ("n_sites", "n_violations")
FLOATS = ("violation_rate",)
REQUIRED = set(INTS) | set(FLOATS)
TOL = 1e-4


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")

try:
    actual = json.loads(OUT.read_text())
except json.JSONDecodeError as exc:
    fail(f"{OUT} not valid JSON: {exc}")

if not isinstance(actual, dict) or set(actual) != REQUIRED:
    fail(f"keys mismatch: actual={sorted(actual) if isinstance(actual, dict) else '?'} "
         f"required={sorted(REQUIRED)}")

gold = json.loads(GOLD.read_text())

for k in INTS:
    if not isinstance(actual[k], int):
        fail(f"{k} must be int")
    if actual[k] != gold[k]:
        fail(f"{k}: actual={actual[k]} gold={gold[k]}")

for k in FLOATS:
    if not isinstance(actual[k], (int, float)):
        fail(f"{k} must be numeric")
    if abs(float(actual[k]) - float(gold[k])) > TOL:
        fail(f"{k}: actual={actual[k]} gold={gold[k]} tol={TOL}")

print(f"ok: {actual}")
sys.exit(0)
