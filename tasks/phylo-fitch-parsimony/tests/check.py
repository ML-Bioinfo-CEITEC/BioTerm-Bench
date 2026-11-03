#!/usr/bin/env python3
"""Grader for phylo-fitch-parsimony.

The expected answer is embedded here rather than mounted from ../gold: Harbor
uploads tests/ only at verification time, so nothing in this file is visible to
the agent while it works.
"""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/parsimony.tsv")

EXPECTED = """\
site	n_distinct_bases	parsimony_score
1	4	3
2	2	1
3	2	1
4	2	2
5	3	2
6	3	3
7	2	2
8	2	1
9	1	0
10	3	2
11	4	3
12	4	4
13	1	0
14	2	1
15	2	1
16	3	3
17	3	2
18	2	1
19	3	2
20	2	1
21	3	2
22	1	0
23	2	1
24	4	4
25	2	2
26	2	1
27	2	2
28	3	2
29	3	3
30	3	3
31	4	3
32	2	2
33	3	2
34	3	2
35	2	1
36	3	2
37	2	1
38	2	1
39	2	1
40	2	1
41	1	0
42	1	0
43	3	2
44	2	1
45	2	1
46	3	3
47	3	2
48	2	1
49	1	0
50	2	1
51	1	0
52	3	2
53	2	1
54	2	1
55	2	1
56	3	2
57	3	4
58	2	2
59	2	3
60	2	1
61	1	0
62	1	0
63	2	1
64	2	2
65	3	2
66	4	4
67	2	3
68	1	0
69	3	2
70	3	3
71	1	0
72	1	0
73	3	3
74	3	2
75	3	2
76	1	0
77	2	1
78	2	1
79	3	2
80	3	2
81	3	2
82	2	3
83	1	0
84	2	2
85	3	2
86	2	1
87	2	1
88	2	1
89	3	2
90	3	2
91	3	2
92	3	4
93	3	2
94	3	4
95	3	3
96	2	3
97	3	2
98	2	1
99	1	0
100	3	3
101	3	3
102	1	0
103	2	1
104	2	1
105	1	0
106	1	0
107	2	1
108	2	1
109	1	0
110	3	2
111	2	2
112	2	2
113	1	0
114	2	1
115	2	2
116	3	2
117	2	1
118	2	2
119	3	3
120	2	1
121	2	1
122	2	1
123	2	2
124	3	3
125	4	5
126	3	2
127	2	1
128	2	2
129	2	1
130	3	2
131	3	2
132	2	2
133	3	2
134	3	2
135	3	3
136	3	3
137	2	1
138	2	1
139	4	4
140	2	1
141	2	1
142	2	1
143	4	3
144	3	2
145	2	1
146	3	3
147	3	4
148	3	3
149	4	3
150	2	1
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
