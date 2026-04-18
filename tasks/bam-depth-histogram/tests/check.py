#!/usr/bin/env python3
"""Grader for bam-depth-histogram (Pattern C: mixed exact + tolerance)."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

OUT = Path("/app/output/coverage.json")
GOLD = Path("/gold/coverage.json")

EXACT_INT_KEYS = ("ref_length", "median_depth", "max_depth")
FLOAT_KEYS = ("mean_depth", "fraction_covered")
REL = 0.01


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")

try:
    actual = json.loads(OUT.read_text())
except Exception as e:
    fail(f"output JSON not parseable: {e}")

gold = json.loads(GOLD.read_text())

expected = set(EXACT_INT_KEYS) | set(FLOAT_KEYS)
if set(actual.keys()) != expected:
    fail(f"keys differ: actual={sorted(actual)} expected={sorted(expected)}")

for k in EXACT_INT_KEYS:
    if not isinstance(actual[k], int) or isinstance(actual[k], bool):
        fail(f"{k} must be int, got {type(actual[k]).__name__}")
    if actual[k] != gold[k]:
        fail(f"{k} actual={actual[k]} gold={gold[k]} (must be exact)")

for k in FLOAT_KEYS:
    if not isinstance(actual[k], (int, float)) or isinstance(actual[k], bool):
        fail(f"{k} must be numeric, got {type(actual[k]).__name__}")
    if not math.isclose(actual[k], gold[k], rel_tol=REL, abs_tol=1e-6):
        fail(f"{k} actual={actual[k]} gold={gold[k]} (rel_tol={REL})")

if not 0.0 <= actual["fraction_covered"] <= 1.0:
    fail(f"fraction_covered out of [0,1]: {actual['fraction_covered']}")

print(f"ok: depth stats over {actual['ref_length']} positions "
      f"(mean={actual['mean_depth']:.2f}, covered="
      f"{actual['fraction_covered']:.3f})")
sys.exit(0)
