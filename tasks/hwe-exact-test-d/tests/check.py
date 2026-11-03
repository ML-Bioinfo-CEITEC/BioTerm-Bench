#!/usr/bin/env python3
"""Grader for hwe-exact-test-d.

The expected answer is embedded here rather than mounted from ../gold: Harbor
uploads tests/ only at verification time, so nothing in this file is visible to
the agent while it works.
"""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/result.tsv")

EXPECTED = """\
variant	hom_ref	heterozygous	hom_alt	minor_allele_count	exact_p	fails_hwe
v001	35	12	23	58	0.00000005	1
v002	27	21	22	65	0.00084769	1
v003	25	25	20	65	0.01795488	1
v004	35	11	24	59	0.00000001	1
v005	55	4	11	26	0.00000000	1
v006	38	14	18	50	0.00000301	1
v007	38	12	20	52	0.00000009	1
v008	23	24	23	70	0.00890444	1
v009	43	12	15	42	0.00000134	1
v010	26	15	29	67	0.00000120	1
v011	34	16	20	56	0.00001286	1
v012	44	11	15	41	0.00000043	1
v013	14	29	27	57	0.22610977	0
v014	48	5	17	39	0.00000000	1
v015	17	28	25	62	0.14455506	0
v016	46	3	21	45	0.00000000	1
v017	37	10	23	56	0.00000000	1
v018	59	2	9	20	0.00000000	1
v019	39	13	18	49	0.00000078	1
v020	24	21	25	69	0.00081682	1
v021	26	17	27	69	0.00001385	1
v022	21	16	33	58	0.00000808	1
v023	21	23	26	65	0.00438609	1
v024	36	10	24	58	0.00000000	1
v025	55	3	12	27	0.00000000	1
v026	40	11	19	49	0.00000004	1
v027	49	7	14	35	0.00000000	1
v028	55	2	13	28	0.00000000	1
v029	21	27	22	69	0.05815617	0
v030	52	2	16	34	0.00000000	1
v031	27	19	24	67	0.00012334	1
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
