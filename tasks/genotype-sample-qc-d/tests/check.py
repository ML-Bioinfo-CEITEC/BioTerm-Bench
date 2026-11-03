#!/usr/bin/env python3
"""Grader for genotype-sample-qc-d.

The expected answer is embedded here rather than mounted from ../gold: Harbor
uploads tests/ only at verification time, so nothing in this file is visible to
the agent while it works.
"""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/result.tsv")

EXPECTED = """\
sample	called	missing	call_rate	heterozygous	heterozygosity	alt_alleles
S01	75	10	0.882353	22	0.293333	50
S02	70	15	0.823529	24	0.342857	36
S03	66	19	0.776471	23	0.348485	37
S04	68	17	0.800000	23	0.338235	31
S05	77	8	0.905882	22	0.285714	42
S06	72	13	0.847059	17	0.236111	27
S07	72	13	0.847059	28	0.388889	42
S08	64	21	0.752941	27	0.421875	33
S09	64	21	0.752941	21	0.328125	41
S10	69	16	0.811765	22	0.318841	40
S11	73	12	0.858824	25	0.342466	41
S12	66	19	0.776471	22	0.333333	36
S13	71	14	0.835294	22	0.309859	34
S14	74	11	0.870588	28	0.378378	48
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
