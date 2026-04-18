#!/usr/bin/env python3
"""Grader for snpeff-annotate-counts (Pattern A: exact integer match)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path("/app/output/impact_counts.json")
GOLD = Path("/gold/impact_counts.json")

KEYS = ("HIGH", "MODERATE", "LOW", "MODIFIER", "total")


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

if set(actual.keys()) != set(KEYS):
    fail(f"keys differ: actual={sorted(actual)} expected={sorted(KEYS)}")

for k in KEYS:
    if not isinstance(actual[k], int) or isinstance(actual[k], bool):
        fail(f"{k} must be int, got {type(actual[k]).__name__}")
    if actual[k] < 0:
        fail(f"{k} must be non-negative, got {actual[k]}")
    if actual[k] != gold[k]:
        fail(f"{k} actual={actual[k]} gold={gold[k]}")

subtotal = actual["HIGH"] + actual["MODERATE"] + actual["LOW"] + actual["MODIFIER"]
if subtotal > actual["total"]:
    fail(f"impact subtotal {subtotal} exceeds total {actual['total']}")

print(f"ok: impact counts match gold (total={actual['total']}, "
      f"H={actual['HIGH']} M={actual['MODERATE']} L={actual['LOW']} "
      f"Mod={actual['MODIFIER']})")
sys.exit(0)
