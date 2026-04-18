#!/usr/bin/env python3
"""Grader for insert-size-stats (Pattern C: numeric tolerance)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path("/app/output/insert.json")
GOLD = Path("/gold/insert.json")
REQUIRED = {"mean_insert", "stdev_insert"}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")

try:
    actual = json.loads(OUT.read_text())
except json.JSONDecodeError as exc:
    fail(f"{OUT} not valid JSON: {exc}")

if not isinstance(actual, dict) or set(actual.keys()) != REQUIRED:
    fail(f"keys {sorted(actual) if isinstance(actual, dict) else 'N/A'} "
         f"!= required {sorted(REQUIRED)}")

gold = json.loads(GOLD.read_text())
for k in sorted(REQUIRED):
    tol = float(gold.get(f"{k}_tol", 0.0))
    try:
        av = float(actual[k])
        gv = float(gold[k])
    except (TypeError, ValueError):
        fail(f"{k} is not numeric: {actual[k]!r}")
    if abs(av - gv) > tol:
        fail(f"{k} actual={av} gold={gv} |diff|>{tol}")

print(f"ok: insert stats within tolerance "
      f"(mean={actual['mean_insert']} stdev={actual['stdev_insert']})")
sys.exit(0)
