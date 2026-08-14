#!/usr/bin/env python3
"""Grader for kmer-contamination-mixture (Pattern A)."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

OUT = Path("/app/output/mixture.tsv")
GOLD = Path("/gold/mixture.tsv")
ORDER = ["alpha", "beta", "gamma", "delta", "ambiguous", "unassigned"]


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail("missing /app/output/mixture.tsv")


def load(path: Path) -> list[dict[str, str]]:
    with path.open() as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    if list(rows[0].keys()) != ["label", "read_count", "fraction"]:
        fail(f"bad header in {path}")
    return rows


actual = load(OUT)
gold = load(GOLD)

if [row["label"] for row in actual] != ORDER:
    fail("row order differs from required label order")
if actual != gold:
    fail(f"output differs from gold\nactual={actual}\ngold={gold}")

print("ok: mixture table matches gold exactly")
