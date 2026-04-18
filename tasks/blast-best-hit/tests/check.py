#!/usr/bin/env python3
"""Grader for blast-best-hit (Pattern A with trailing-pipe tolerance)."""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/best_hits.tsv")
GOLD = Path("/gold/best_hits.tsv")
QUERIES = Path("/app/data/queries.fasta")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def load_tsv(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            fail(f"{path} line {lineno}: expected 2 columns, got {len(parts)}")
        rows.append((parts[0], parts[1].rstrip("|")))
    return rows


if not OUT.is_file():
    fail(f"missing {OUT}")

actual = load_tsv(OUT)
gold = load_tsv(GOLD)

# Every query appears exactly once
query_ids = [line[1:].split()[0] for line in QUERIES.read_text().splitlines()
             if line.startswith(">")]
actual_qids = [r[0] for r in actual]
if sorted(actual_qids) != sorted(query_ids):
    fail(f"query set mismatch actual={sorted(actual_qids)} expected={sorted(query_ids)}")
if len(set(actual_qids)) != len(actual_qids):
    fail("duplicate query rows in output")

if [q for q, _ in actual] != sorted(query_ids):
    fail("rows not alphabetically sorted by query_id")

actual_map = dict(actual)
gold_map = dict(gold)
for q in query_ids:
    if actual_map[q] != gold_map[q]:
        fail(f"query {q}: actual={actual_map[q]} gold={gold_map[q]}")

print(f"ok: {len(actual)} best-hit rows match gold")
sys.exit(0)
