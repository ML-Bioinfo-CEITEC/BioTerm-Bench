#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

COUNTS = Path("/app/output/gene_counts.tsv")
SUMMARY = Path("/app/output/assignment_summary.tsv")
GOLD_COUNTS = Path("/tests/gold/gene_counts.tsv")
GOLD_SUMMARY = Path("/tests/gold/assignment_summary.tsv")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def compare(actual: Path, gold: Path, label: str) -> None:
    if not actual.is_file():
        fail(f"missing {actual}")
    a_text = actual.read_text()
    g_text = gold.read_text()
    if a_text != g_text:
        a_lines = a_text.splitlines()
        g_lines = g_text.splitlines()
        for i, (a_line, g_line) in enumerate(zip(a_lines, g_lines), start=1):
            if a_line != g_line:
                fail(f"{label} differs at line {i}: actual={a_line!r} gold={g_line!r}")
        fail(
            f"{label} length mismatch: actual={len(a_lines)} lines gold={len(g_lines)} lines"
        )


compare(COUNTS, GOLD_COUNTS, "gene_counts.tsv")
compare(SUMMARY, GOLD_SUMMARY, "assignment_summary.tsv")
print("ok: featureCounts matrix and summary match gold")
