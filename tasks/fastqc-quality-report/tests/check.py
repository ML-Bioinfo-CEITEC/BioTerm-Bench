#!/usr/bin/env python3
"""Grader for fastqc-quality-report (Pattern C)."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

OUT = Path("/app/output/qc_summary.json")
GOLD = Path("/gold/qc_summary.json")

INT_KEYS = ("total_sequences", "sequence_length_min", "sequence_length_max", "gc_content")
FLOAT_KEYS = ("per_base_q20_frac",)


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
        fail(f"{k} actual={actual[k]} gold={gold[k]} (exact)")

for k in FLOAT_KEYS:
    if not isinstance(actual[k], (int, float)) or isinstance(actual[k], bool):
        fail(f"{k} must be numeric, got {type(actual[k]).__name__}")
    if not math.isclose(actual[k], gold[k], rel_tol=0.05, abs_tol=1e-6):
        fail(f"{k} actual={actual[k]} gold={gold[k]} (rel_tol=0.05)")

print(f"ok: 5 QC stats within tolerance")
sys.exit(0)
