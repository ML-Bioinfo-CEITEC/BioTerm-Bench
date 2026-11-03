#!/usr/bin/env python3
"""Grader for cigar-consumption-ledger-c.

The expected answer is embedded here rather than mounted from ../gold: Harbor
uploads tests/ only at verification time, so nothing in this file is visible to
the agent while it works.
"""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/result.tsv")

EXPECTED = """\
read_id	cigar	reference_span	query_consumed	aligned_bases	inserted_bases	deleted_bases	skipped_bases	clipped_bases
read001	17M19X11=15N12H21I	62	68	47	21	0	15	12
read002	2M14N12X12=21=14M	75	61	61	0	0	14	0
read003	6M4P17M10D17S12S	33	52	23	0	10	0	29
read004	18M24P21M18D1X1P	58	40	40	0	18	0	0
read005	5M24H22X20I9X3D	39	56	36	20	3	0	24
read006	5M5P15I1I19S9P	5	40	5	16	0	0	19
read007	16M6P6P16S11M3I	27	46	27	3	0	0	16
read008	6M3M13H6S24X20S	33	59	33	0	0	0	39
read009	14M21M7S24X4=7S	63	77	63	0	0	0	14
read010	5M7S15I12N11N19P	28	27	5	15	0	23	7
read011	13M10S11P15X17H9H	28	38	28	0	0	0	36
read012	17M17I9M2D18=5D	51	61	44	17	7	0	0
read013	11M9=15S5S12D22X	54	62	42	0	12	0	20
read014	5M23X13S14X17M18=	77	90	77	0	0	0	13
read015	3M2I7H3M21M4M	31	33	31	2	0	0	7
read016	11M19=24N2D9H15X	71	45	45	0	2	24	9
read017	13M16M19P18X16M10X	73	73	73	0	0	0	0
read018	10M6S18N12S18N11D	57	28	10	0	11	36	18
read019	8M3D9D13S17H4H	20	21	8	0	12	0	34
read020	18M7D6N13I12S6H	31	43	18	13	7	6	18
read021	13M10S23N2=1I3I	38	29	15	4	0	23	10
read022	17M5S11=15D2X7P	45	35	30	0	15	0	5
read023	24M21M2N20I19P10D	57	65	45	20	10	2	0
read024	2M12S24H14I23S7X	9	58	9	14	0	0	59
read025	18M8X14N23=1I23D	86	50	49	1	23	14	0
read026	18M11D11=15M22S14P	55	66	44	0	11	0	22
read027	22M21X6X7P23P13N	62	49	49	0	0	13	0
read028	11M4M8M23X14M15D	75	60	60	0	15	0	0
read029	9M16S23D14M12S16D	62	51	23	0	39	0	28
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
