#!/usr/bin/env python3
"""Grader for tpm-normalize (Pattern C: relative tolerance per cell)."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

OUT = Path("/app/output/tpm.tsv")
GOLD = Path("/gold/tpm.tsv")
COUNTS = Path("/app/data/counts.tsv")

REL = 0.01
SUM_REL = 1e-3


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")

try:
    actual = pd.read_csv(OUT, sep="\t")
except Exception as e:
    fail(f"could not parse {OUT}: {e}")

gold = pd.read_csv(GOLD, sep="\t")
counts = pd.read_csv(COUNTS, sep="\t")

if list(actual.columns) != list(gold.columns):
    fail(f"columns differ: actual={list(actual.columns)} gold={list(gold.columns)}")

if list(actual["gene_id"]) != list(counts["gene_id"]):
    fail("gene_id order / values differ from counts.tsv")

samples = [c for c in gold.columns if c != "gene_id"]

for s in samples:
    col_sum = actual[s].sum()
    if not math.isclose(col_sum, 1_000_000.0, rel_tol=SUM_REL, abs_tol=1e-6):
        fail(f"sample {s} TPM sum = {col_sum}, expected ~1e6 (rel_tol={SUM_REL})")

# Per-cell check
for g_idx in range(len(gold)):
    for s in samples:
        a = float(actual.iloc[g_idx][s])
        b = float(gold.iloc[g_idx][s])
        if not math.isclose(a, b, rel_tol=REL, abs_tol=1e-3):
            fail(f"gene {gold.iloc[g_idx]['gene_id']} sample {s} "
                 f"actual={a} gold={b} (rel_tol={REL})")

print(f"ok: {len(actual)} genes x {len(samples)} samples within tolerance, "
      f"column sums == 1e6")
sys.exit(0)
