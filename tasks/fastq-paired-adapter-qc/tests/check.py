#!/usr/bin/env python3
"""Grader for fastq-paired-adapter-qc."""
from __future__ import annotations

import json
import sys
from pathlib import Path

SUMMARY_OUT = Path("/app/output/summary.json")
SUMMARY_GOLD = Path("/tests/gold/summary.json")
ORPHAN_OUT = Path("/app/output/orphans.tsv")
ORPHAN_GOLD = Path("/tests/gold/orphans.tsv")
REQUIRED = {
    "adapter_pairs",
    "adapter_pairs_both_mates",
    "orphan_r1",
    "orphan_r2",
    "proper_pairs",
    "q30_frac_r1",
    "q30_frac_r2",
    "total_r1",
    "total_r2",
}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not SUMMARY_OUT.is_file():
    fail(f"missing {SUMMARY_OUT}")
if not ORPHAN_OUT.is_file():
    fail(f"missing {ORPHAN_OUT}")

actual = json.loads(SUMMARY_OUT.read_text())
gold = json.loads(SUMMARY_GOLD.read_text())
if set(actual) != REQUIRED:
    fail(f"summary keys mismatch: actual={sorted(actual)} required={sorted(REQUIRED)}")
if actual != gold:
    fail("summary.json differs from gold")

orphan_actual = ORPHAN_OUT.read_text().splitlines()
orphan_gold = ORPHAN_GOLD.read_text().splitlines()
if not orphan_actual or orphan_actual[0] != "read_id\tpresent_in":
    fail("orphans.tsv header mismatch")
if orphan_actual != orphan_gold:
    fail("orphans.tsv differs from gold")

print("ok: paired FASTQ QC outputs match gold")
