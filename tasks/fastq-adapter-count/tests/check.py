#!/usr/bin/env python3
"""Grader for fastq-adapter-count (Pattern A: exact value match)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path("/app/output/counts.json")
GOLD = Path("/gold/counts.json")

REQUIRED = {"total_reads", "adapter_reads", "adapter_seq"}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")

try:
    actual = json.loads(OUT.read_text())
except json.JSONDecodeError as exc:
    fail(f"{OUT} is not valid JSON: {exc}")

if not isinstance(actual, dict):
    fail("counts.json must be a JSON object")
if set(actual.keys()) != REQUIRED:
    fail(f"keys {sorted(actual)} != required {sorted(REQUIRED)}")

gold = json.loads(GOLD.read_text())
for k in sorted(REQUIRED):
    if actual[k] != gold[k]:
        fail(f"{k}: actual={actual[k]!r} gold={gold[k]!r}")

# Sanity: counts are non-negative ints, adapter_reads <= total_reads.
if not isinstance(actual["total_reads"], int) or actual["total_reads"] < 0:
    fail("total_reads must be non-negative integer")
if not isinstance(actual["adapter_reads"], int) or actual["adapter_reads"] < 0:
    fail("adapter_reads must be non-negative integer")
if actual["adapter_reads"] > actual["total_reads"]:
    fail("adapter_reads > total_reads")

print(f"ok: total={actual['total_reads']} adapter={actual['adapter_reads']}")
sys.exit(0)
