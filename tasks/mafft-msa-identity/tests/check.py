#!/usr/bin/env python3
"""Grader for mafft-msa-identity (Pattern C per-row)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/identity.tsv")
GOLD = Path("/gold/identity.tsv")
TOL = 5e-3     # 0.5% abs tolerance on identity


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def parse(path: Path) -> list[tuple[str, str, float]]:
    lines = [l.rstrip("\r") for l in path.read_text().splitlines() if l.strip()]
    if not lines or lines[0].split("\t") != ["seq_a", "seq_b", "identity"]:
        fail(f"{path} header must be 'seq_a\\tseq_b\\tidentity'")
    rows = []
    for i, line in enumerate(lines[1:], 2):
        parts = line.split("\t")
        if len(parts) != 3:
            fail(f"{path} line {i} not 3 columns: {line!r}")
        try:
            ident = float(parts[2])
        except ValueError:
            fail(f"{path} line {i} identity not float: {line!r}")
        if not 0.0 <= ident <= 1.0:
            fail(f"{path} line {i} identity out of range [0,1]: {ident}")
        if parts[0] >= parts[1]:
            fail(f"{path} line {i} expected seq_a < seq_b, got {parts[:2]}")
        rows.append((parts[0], parts[1], ident))
    return rows


if not OUT.is_file():
    fail(f"missing {OUT}")

actual = parse(OUT)
gold = parse(GOLD)

a_dict = {(a, b): v for a, b, v in actual}
g_dict = {(a, b): v for a, b, v in gold}

if set(a_dict) != set(g_dict):
    missing = set(g_dict) - set(a_dict)
    extra = set(a_dict) - set(g_dict)
    fail(f"row-set mismatch: {len(missing)} missing, {len(extra)} extra")

bad = [(k, a_dict[k], g_dict[k]) for k in g_dict if abs(a_dict[k] - g_dict[k]) > TOL]
if bad:
    fail(f"{len(bad)} identity values differ >{TOL}: first={bad[:3]}")

# Sort check.
pairs = [(a, b) for a, b, _ in actual]
if pairs != sorted(pairs):
    fail("rows not sorted ascending by (seq_a, seq_b)")

print(f"ok: {len(actual)} identity pairs within tolerance {TOL}")
sys.exit(0)
