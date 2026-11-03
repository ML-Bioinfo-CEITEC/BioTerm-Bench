#!/usr/bin/env python3
"""Grader for fasta-longest-orf (Pattern A: exact diff)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/orf.tsv")
GOLD = Path("/tests/gold/orf.tsv")
HEADER = ["seq_id", "strand", "frame", "start", "end", "length"]


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")

actual = [l.rstrip("\r") for l in OUT.read_text().splitlines() if l.strip()]
gold = [l.rstrip("\r") for l in GOLD.read_text().splitlines() if l.strip()]

if len(actual) != 2:
    fail(f"expected 2 non-empty lines (header + 1 ORF), got {len(actual)}")

if actual[0].split("\t") != HEADER:
    fail(f"header row must be tab-separated {HEADER}, got {actual[0].split(chr(9))}")

if actual != gold:
    fail(f"row mismatch\n  actual: {actual[1]!r}\n    gold: {gold[1]!r}")

# Sanity-check the values are internally consistent.
cols = actual[1].split("\t")
try:
    strand = cols[1]
    frame = int(cols[2])
    start = int(cols[3])
    end = int(cols[4])
    length = int(cols[5])
except (IndexError, ValueError):
    fail(f"non-integer fields in data row: {cols}")

if strand not in {"+", "-"}:
    fail(f"strand must be '+' or '-', got {strand!r}")
if frame not in {0, 1, 2}:
    fail(f"frame must be 0/1/2, got {frame}")
if start < 1 or end < start:
    fail(f"invalid coords start={start} end={end}")
if length != end - start + 1:
    fail(f"length {length} != end-start+1 ({end - start + 1})")

print(f"ok: longest ORF matches gold ({strand} f{frame} {start}-{end} len={length})")
sys.exit(0)
