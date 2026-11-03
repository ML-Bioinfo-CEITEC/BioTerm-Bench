#!/usr/bin/env python3
"""Grader for vcf-phase-blocks.

The expected answer is embedded here rather than mounted from ../gold: Harbor
uploads tests/ only at verification time, so nothing in this file is visible to
the agent while it works.
"""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/phase_blocks.tsv")

EXPECTED = """\
chrom	phase_set	n_variants	start	end	span	max_gap
chr1	40997	7	41291	54515	13225	3872
chr1	69704	7	71246	80622	9377	2743
chr1	90850	2	93437	96702	3266	3265
chr1	113923	8	115790	128670	12881	3339
chr1	138423	6	138958	153396	14439	3963
chr1	168318	2	170416	171432	1017	1016
chr2	12955	4	15080	22553	7474	3251
chr2	35617	6	39292	45891	6600	3136
chr2	54238	7	57314	70491	13178	3466
chr2	91429	3	93216	94707	1492	946
chr2	102480	3	104206	107579	3374	1944
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
            if abs(gf - wf) > 1e-06:
                fail(f"line {i} column {col}: actual={gv} gold={wv}")
    print("ok")


main()
