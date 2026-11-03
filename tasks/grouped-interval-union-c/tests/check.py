#!/usr/bin/env python3
"""Grader for grouped-interval-union-c.

The expected answer is embedded here rather than mounted from ../gold: Harbor
uploads tests/ only at verification time, so nothing in this file is visible to
the agent while it works.
"""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/result.tsv")

EXPECTED = """\
group	input_intervals	merged_blocks	raw_length	union_length	duplicated_length
G01	6	2	217	167	50
G02	6	3	269	185	84
G03	6	3	261	183	78
G04	6	3	236	165	71
G05	6	2	240	149	91
G06	6	4	167	127	40
G07	6	2	268	178	90
G08	6	4	226	185	41
G09	6	2	288	173	115
G10	6	1	262	167	95
G11	6	3	264	155	109
G12	6	3	220	176	44
G13	6	3	205	148	57
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
            if abs(gf - wf) > max(5e-05, 1e-08 * abs(wf)):
                fail(f"line {i} column {col}: actual={gv} gold={wv}")
    print("ok")


main()
