#!/usr/bin/env python3
"""Grader for sam-to-cram-roundtrip.

Pattern A-ish: decode the agent's CRAM back to text, canonicalize each
record (join columns with '|') and sort; compare to the gold dump.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

CRAM = Path("/app/output/reads.cram")
CRAI = Path("/app/output/reads.cram.crai")
REF = Path("/app/data/ref.fa")
GOLD = Path("/tests/gold/reads.txt")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not CRAM.is_file() or CRAM.stat().st_size == 0:
    fail(f"missing or empty {CRAM}")
if not CRAI.is_file():
    fail(f"missing CRAM index {CRAI}")

try:
    dump = subprocess.check_output(
        ["bash", "-c",
         f"samtools view -T {REF} {CRAM} | "
         f"awk -F'\\t' '{{print $1\"|\"$2\"|\"$3\"|\"$4\"|\"$5\"|\"$6\"|\"$7\"|\"$8\"|\"$9\"|\"$10\"|\"$11}}' | "
         f"sort"],
        text=True,
    )
except subprocess.CalledProcessError as exc:
    fail(f"samtools view failed on CRAM: {exc}")

gold = GOLD.read_text()
if dump != gold:
    # Report a minimal diff summary.
    a_lines = dump.splitlines()
    g_lines = gold.splitlines()
    only_actual = set(a_lines) - set(g_lines)
    only_gold = set(g_lines) - set(a_lines)
    fail(f"records differ: {len(only_actual)} extra, "
         f"{len(only_gold)} missing (actual={len(a_lines)} gold={len(g_lines)})")

print(f"ok: {len(gold.splitlines())} records match gold after CRAM roundtrip")
sys.exit(0)
