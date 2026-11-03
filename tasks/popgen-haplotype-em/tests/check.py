#!/usr/bin/env python3
"""Grader for popgen-haplotype-em.

The expected answer is embedded here rather than mounted from ../gold: Harbor
uploads tests/ only at verification time, so nothing in this file is visible to
the agent while it works.
"""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/haplotype_freqs.tsv")

EXPECTED = """\
pair_id	haplotype	frequency
pair1	0-0	0.255549
pair1	0-1	0.264451
pair1	1-0	0.206951
pair1	1-1	0.273049
pair2	0-0	0.073235
pair2	0-1	0.234265
pair2	1-0	0.474265
pair2	1-1	0.218235
pair3	0-0	0.406538
pair3	0-1	0.258462
pair3	1-0	0.180962
pair3	1-1	0.154038
pair4	0-0	0.468279
pair4	0-1	0.339221
pair4	1-0	0.119221
pair4	1-1	0.073279
pair5	0-0	0.330043
pair5	0-1	0.137457
pair5	1-0	0.167457
pair5	1-1	0.365043
"""


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def rows(text: str) -> list[list[str]]:
    out = []
    for line in text.replace("\r\n", "\n").split("\n"):
        if not line.strip():
            continue
        out.append(line.rstrip("\n").split("\t"))
    return out


def main() -> None:
    if not OUT.is_file():
        fail(f"missing {OUT}")
    got = rows(OUT.read_text())
    want = rows(EXPECTED)
    if not got:
        fail("output is empty")
    if got[0] != want[0]:
        fail(f"header must be {want[0]}; got {got[0]}")
    if len(got) != len(want):
        fail(f"expected {len(want) - 1} data rows, got {len(got) - 1}")
    ncol = len(want[0])
    for i, (g, w) in enumerate(zip(got[1:], want[1:]), start=2):
        if len(g) != ncol:
            fail(f"line {i}: expected {ncol} tab-separated columns, got {len(g)}")
        for j, (gv, wv) in enumerate(zip(g, w)):
            col = want[0][j]
            try:
                wf = float(wv)
            except ValueError:
                if gv != wv:
                    fail(f"line {i} column {col}: actual={gv} gold={wv}")
                continue
            try:
                gf = float(gv)
            except ValueError:
                fail(f"line {i} column {col}: actual={gv} is not numeric, gold={wv}")
            if abs(gf - wf) > 1e-05:
                fail(f"line {i} column {col}: actual={gv} gold={wv}")
    print("ok")


main()
