#!/usr/bin/env python3
"""Grader for vcf-stats-summary (Pattern C: numeric tolerance)."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

OUT = Path("/app/output/summary.json")
GOLD = Path("/gold/summary.json")

INT_KEYS   = ("n_records", "n_snps", "n_indels")
FLOAT_KEYS = ("ti_tv", "het_hom")
REL_TOL    = 0.01


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

expected_keys = set(INT_KEYS) | set(FLOAT_KEYS)
if set(actual.keys()) != expected_keys:
    fail(f"keys differ: actual={sorted(actual)} expected={sorted(expected_keys)}")

for k in INT_KEYS:
    if not isinstance(actual[k], int) or isinstance(actual[k], bool):
        fail(f"{k} must be int, got {type(actual[k]).__name__}")
    if actual[k] != gold[k]:
        fail(f"{k} actual={actual[k]} gold={gold[k]} (must be exact)")

for k in FLOAT_KEYS:
    if not isinstance(actual[k], (int, float)) or isinstance(actual[k], bool):
        fail(f"{k} must be numeric, got {type(actual[k]).__name__}")
    if not math.isclose(actual[k], gold[k], rel_tol=REL_TOL, abs_tol=1e-9):
        fail(f"{k} actual={actual[k]} gold={gold[k]} (rel_tol={REL_TOL})")

print(f"ok: 5 stats within tolerance (ti_tv={actual['ti_tv']:.3f}, "
      f"het_hom={actual['het_hom']:.3f})")
sys.exit(0)
