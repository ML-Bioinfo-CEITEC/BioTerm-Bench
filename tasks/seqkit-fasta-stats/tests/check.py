#!/usr/bin/env python3
"""Grader for seqkit-fasta-stats (Pattern A: byte-identical TSV)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/stats.tsv")
GOLD = Path("/gold/stats.tsv")
HEADER = ["seq_id", "length", "gc_percent", "n_percent"]


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")

actual = OUT.read_text().splitlines()
gold = GOLD.read_text().splitlines()

if not actual:
    fail("output is empty")
if actual[0].split("\t") != HEADER:
    fail(f"header mismatch: got {actual[0].split(chr(9))}, want {HEADER}")

# Column sanity on actual
for i, line in enumerate(actual[1:], start=2):
    cols = line.split("\t")
    if len(cols) != 4:
        fail(f"line {i}: expected 4 tab-columns, got {len(cols)}")
    try:
        int(cols[1])
    except ValueError:
        fail(f"line {i}: length '{cols[1]}' not integer")
    for name, val in (("gc_percent", cols[2]), ("n_percent", cols[3])):
        if "." not in val:
            fail(f"line {i}: {name}={val!r} must be decimal with 2 places")
        _, frac = val.split(".")
        if len(frac) != 2:
            fail(f"line {i}: {name}={val!r} must have exactly 2 decimals")
        try:
            f = float(val)
        except ValueError:
            fail(f"line {i}: {name}={val!r} not numeric")
        if not 0 <= f <= 100:
            fail(f"line {i}: {name}={f} outside [0,100]")

if actual != gold:
    diff_at = next(
        (i for i, (a, g) in enumerate(zip(actual, gold)) if a != g),
        min(len(actual), len(gold)),
    )
    fail(f"output differs from gold at line {diff_at + 1}:\n"
         f"  actual: {actual[diff_at] if diff_at < len(actual) else '<EOF>'}\n"
         f"  gold:   {gold[diff_at] if diff_at < len(gold) else '<EOF>'}")

print(f"ok: {len(actual) - 1} sequences stats match gold")
sys.exit(0)
