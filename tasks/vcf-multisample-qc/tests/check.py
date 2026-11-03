#!/usr/bin/env python3
"""Grader for vcf-multisample-qc."""
from __future__ import annotations

import sys
from pathlib import Path

FILES = [
    (Path("/app/output/sample_qc.tsv"), Path("/tests/gold/sample_qc.tsv"), "sample\tn_sites\tn_called\tcall_rate\tn_het\thet_rate"),
    (Path("/app/output/pair_concordance.tsv"), Path("/tests/gold/pair_concordance.tsv"), "sample_a\tsample_b\tn_compared\tconcordance"),
]


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


for out, gold, header in FILES:
    if not out.is_file():
        fail(f"missing {out}")
    actual = out.read_text().splitlines()
    expected = gold.read_text().splitlines()
    if not actual or actual[0] != header:
        fail(f"{out.name}: header must be exactly '{header}'")
    if actual != expected:
        fail(f"{out.name}: output differs from gold")

print("ok: multisample QC tables match gold")
