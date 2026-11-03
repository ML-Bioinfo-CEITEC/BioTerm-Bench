#!/usr/bin/env python3
"""Grader for vcf-denovo-strict.

The expected answer is embedded here rather than mounted from ../gold: Harbor
uploads tests/ only at verification time, so nothing in this file is visible to
the agent while it works.
"""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/denovo.tsv")

EXPECTED = """\
chrom	pos	ref	alt	class	child_ab
chr1	11835	T	C	uncertain	0.7500
chr1	17522	A	G	denovo	0.5500
chr1	22974	C	T	uncertain	0.1250
chr1	25171	T	C	denovo	0.5000
chr1	26779	T	C	uncertain	0.1200
chr1	27280	C	T	uncertain	0.5000
chr1	29061	G	A	uncertain	0.2500
chr1	48033	G	A	denovo	0.3000
chr1	62279	T	C	uncertain	0.5000
chr1	66274	A	G	uncertain	0.2000
chr1	71002	G	A	uncertain	0.7500
chr1	85199	C	T	uncertain	0.2500
chr1	93111	G	A	uncertain	0.5500
chr1	95979	G	A	uncertain	0.5000
chr1	96549	G	A	uncertain	0.3333
chr1	99513	A	G	uncertain	0.8000
chr1	105265	T	C	uncertain	0.8000
chr1	107699	C	T	uncertain	0.5000
chr1	113971	T	C	uncertain	0.1111
chr1	118928	G	A	uncertain	0.8000
chr1	119469	A	G	uncertain	0.5000
chr1	121723	A	G	denovo	0.4667
chr2	16601	G	A	uncertain	0.3000
chr2	23801	A	G	uncertain	0.5000
chr2	25834	C	T	denovo	0.5600
chr2	26274	A	G	uncertain	0.3000
chr2	35882	T	C	denovo	0.5000
chr2	40558	C	T	uncertain	0.4444
chr2	46636	T	C	uncertain	0.2000
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
            if abs(gf - wf) > 5e-05:
                fail(f"line {i} column {col}: actual={gv} gold={wv}")
    print("ok")


main()
