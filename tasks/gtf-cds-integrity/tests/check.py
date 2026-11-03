#!/usr/bin/env python3
"""Grader for gtf-cds-integrity.

The expected answer is embedded here rather than mounted from ../gold: Harbor
uploads tests/ only at verification time, so nothing in this file is visible to
the agent while it works.
"""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/cds_report.tsv")

EXPECTED = """\
tx_id	chrom	strand	cds_len	has_start	has_stop	n_internal_stops	status
TX0001	ctg1	-	9	yes	yes	0	ok
TX0002	ctg2	-	39	yes	yes	0	ok
TX0003	ctg2	+	6	yes	yes	0	ok
TX0004	ctg2	-	17	yes	no	0	not_multiple_of_three
TX0005	ctg2	+	21	yes	no	0	no_stop_codon
TX0006	ctg1	+	36	yes	yes	0	ok
TX0007	ctg1	-	15	yes	yes	0	ok
TX0008	ctg2	+	39	no	yes	0	no_start_codon
TX0009	ctg1	+	39	yes	yes	0	ok
TX0010	ctg1	-	35	yes	no	0	not_multiple_of_three
TX0011	ctg1	-	42	yes	yes	0	ok
TX0012	ctg1	+	24	yes	yes	0	ok
TX0013	ctg2	-	18	yes	no	0	no_stop_codon
TX0014	ctg2	+	9	yes	yes	0	ok
TX0015	ctg1	+	9	yes	yes	0	ok
TX0016	ctg1	-	30	yes	yes	1	internal_stop
TX0017	ctg1	+	33	yes	yes	0	ok
TX0018	ctg1	+	24	yes	no	0	no_stop_codon
TX0019	ctg1	+	32	yes	no	0	not_multiple_of_three
TX0020	ctg1	+	30	yes	no	0	no_stop_codon
TX0021	ctg1	-	6	yes	yes	0	ok
TX0022	ctg2	-	30	no	yes	0	no_start_codon
TX0023	ctg2	-	9	yes	yes	1	internal_stop
TX0024	ctg2	+	6	yes	yes	0	ok
TX0025	ctg1	-	18	yes	no	0	no_stop_codon
TX0026	ctg2	+	33	yes	yes	0	ok
TX0027	ctg2	-	15	yes	yes	0	ok
TX0028	ctg1	+	21	yes	yes	0	ok
TX0029	ctg2	-	18	yes	yes	1	internal_stop
TX0030	ctg2	-	24	yes	yes	0	ok
TX0031	ctg1	-	48	yes	yes	0	ok
TX0032	ctg2	+	9	yes	yes	1	internal_stop
TX0033	ctg1	-	6	yes	yes	0	ok
TX0034	ctg1	+	42	yes	yes	0	ok
TX0035	ctg1	+	12	yes	yes	0	ok
TX0036	ctg1	-	23	yes	no	0	not_multiple_of_three
TX0037	ctg1	-	24	yes	yes	0	ok
TX0038	ctg1	-	24	yes	yes	0	ok
TX0039	ctg2	+	18	yes	yes	0	ok
TX0040	ctg2	+	18	no	yes	0	no_start_codon
TX0041	ctg1	-	6	yes	yes	0	ok
TX0042	ctg1	+	35	yes	no	0	not_multiple_of_three
TX0043	ctg1	+	24	no	yes	0	no_start_codon
TX0044	ctg2	+	27	yes	yes	1	internal_stop
TX0045	ctg1	+	15	yes	yes	1	internal_stop
TX0046	ctg2	-	12	yes	no	0	no_stop_codon
TX0047	ctg2	+	21	yes	no	0	no_stop_codon
TX0048	ctg2	-	42	no	yes	0	no_start_codon
TX0049	ctg1	-	6	yes	yes	0	ok
TX0050	ctg1	-	12	yes	yes	1	internal_stop
TX0051	ctg1	+	39	yes	yes	1	internal_stop
TX0052	ctg2	-	39	no	yes	0	no_start_codon
TX0053	ctg2	-	30	yes	yes	0	ok
TX0054	ctg1	+	15	yes	no	0	no_stop_codon
TX0055	ctg2	-	33	yes	yes	0	ok
TX0056	ctg2	+	23	yes	no	0	not_multiple_of_three
TX0057	ctg1	+	36	yes	yes	0	ok
TX0058	ctg1	+	12	yes	yes	0	ok
TX0059	ctg2	-	15	yes	yes	0	ok
TX0060	ctg2	-	27	no	yes	0	no_start_codon
TX0061	ctg1	+	18	yes	no	0	no_stop_codon
TX0062	ctg1	+	24	yes	yes	1	internal_stop
TX0063	ctg2	-	36	yes	yes	0	ok
TX0064	ctg1	+	45	yes	no	0	no_stop_codon
TX0065	ctg2	+	42	yes	yes	0	ok
TX0066	ctg1	-	39	yes	yes	1	internal_stop
TX0067	ctg2	-	51	yes	yes	0	ok
TX0068	ctg1	-	42	no	yes	0	no_start_codon
TX0069	ctg2	-	18	yes	yes	0	ok
TX0070	ctg1	+	36	yes	no	0	no_stop_codon
TX0071	ctg1	+	24	yes	yes	0	ok
TX0072	ctg1	-	21	yes	yes	0	ok
TX0073	ctg1	+	32	yes	no	0	not_multiple_of_three
TX0074	ctg2	+	33	yes	yes	0	ok
TX0075	ctg2	-	21	yes	yes	0	ok
TX0076	ctg1	-	6	yes	no	0	no_stop_codon
TX0077	ctg1	-	9	yes	yes	0	ok
TX0078	ctg1	+	48	yes	yes	0	ok
TX0079	ctg2	+	24	yes	yes	0	ok
TX0080	ctg2	+	18	yes	no	0	no_stop_codon
TX0081	ctg2	-	26	yes	no	0	not_multiple_of_three
TX0082	ctg2	-	15	no	yes	0	no_start_codon
TX0083	ctg2	-	18	no	yes	0	no_start_codon
TX0084	ctg2	-	29	yes	no	0	not_multiple_of_three
TX0085	ctg1	-	30	no	yes	0	no_start_codon
TX0086	ctg1	+	27	yes	no	0	no_stop_codon
TX0087	ctg1	+	51	yes	yes	1	internal_stop
TX0088	ctg1	-	30	no	yes	0	no_start_codon
TX0089	ctg2	+	39	yes	yes	0	ok
TX0090	ctg2	+	12	yes	yes	0	ok
TX0091	ctg2	-	27	yes	yes	0	ok
TX0092	ctg1	+	30	yes	yes	0	ok
TX0093	ctg2	-	6	yes	yes	0	ok
TX0094	ctg2	+	27	yes	yes	0	ok
TX0095	ctg2	-	8	yes	no	0	not_multiple_of_three
TX0096	ctg1	+	24	yes	yes	0	ok
TX0097	ctg1	+	24	yes	yes	0	ok
TX0098	ctg2	-	21	yes	yes	1	internal_stop
TX0099	ctg1	+	42	yes	yes	0	ok
TX0100	ctg1	-	33	yes	yes	0	ok
TX0101	ctg1	-	30	yes	yes	1	internal_stop
TX0102	ctg1	-	35	yes	no	0	not_multiple_of_three
TX0103	ctg2	+	21	yes	yes	0	ok
TX0104	ctg1	+	18	yes	yes	0	ok
TX0105	ctg1	+	33	yes	yes	0	ok
TX0106	ctg2	+	9	no	yes	0	no_start_codon
TX0107	ctg1	+	24	yes	yes	0	ok
TX0108	ctg1	-	12	yes	yes	0	ok
TX0109	ctg1	-	12	yes	yes	0	ok
TX0110	ctg1	+	26	yes	no	0	not_multiple_of_three
TX0111	ctg1	-	33	yes	yes	0	ok
TX0112	ctg1	+	6	no	yes	0	no_start_codon
TX0113	ctg2	+	33	yes	yes	0	ok
TX0114	ctg1	-	30	yes	yes	0	ok
TX0115	ctg2	-	18	yes	yes	0	ok
TX0116	ctg2	+	9	yes	yes	0	ok
TX0117	ctg2	+	12	yes	yes	0	ok
TX0118	ctg2	+	12	yes	yes	1	internal_stop
TX0119	ctg1	-	6	yes	yes	0	ok
TX0120	ctg1	-	21	no	yes	0	no_start_codon
TX0121	ctg2	+	12	yes	yes	0	ok
TX0122	ctg2	+	33	yes	yes	0	ok
TX0123	ctg1	-	9	yes	yes	0	ok
TX0124	ctg2	+	54	no	yes	0	no_start_codon
TX0125	ctg1	+	27	yes	yes	0	ok
TX0126	ctg1	-	27	yes	yes	0	ok
TX0127	ctg2	+	23	yes	no	0	not_multiple_of_three
TX0128	ctg1	-	6	yes	no	0	no_stop_codon
TX0129	ctg2	-	27	yes	yes	0	ok
TX0130	ctg2	+	21	yes	yes	0	ok
TX0131	ctg2	+	33	yes	yes	0	ok
TX0132	ctg2	-	12	yes	yes	0	ok
TX0133	ctg1	-	39	yes	yes	1	internal_stop
TX0134	ctg1	-	24	yes	yes	0	ok
TX0135	ctg1	+	18	yes	yes	0	ok
TX0136	ctg2	-	36	yes	yes	1	internal_stop
TX0137	ctg1	-	15	yes	no	0	no_stop_codon
TX0138	ctg1	-	36	yes	yes	0	ok
TX0139	ctg1	-	39	yes	yes	0	ok
TX0140	ctg2	+	6	yes	yes	0	ok
TX0141	ctg2	-	35	yes	no	0	not_multiple_of_three
TX0142	ctg1	+	30	yes	yes	1	internal_stop
TX0143	ctg2	+	24	yes	yes	0	ok
TX0144	ctg2	-	33	yes	yes	0	ok
TX0145	ctg2	-	33	yes	yes	1	internal_stop
TX0146	ctg1	-	21	yes	yes	0	ok
TX0147	ctg2	+	45	yes	yes	0	ok
TX0148	ctg1	+	15	no	yes	0	no_start_codon
TX0149	ctg1	-	11	yes	no	0	not_multiple_of_three
TX0150	ctg2	-	24	yes	yes	0	ok
TX0151	ctg1	+	6	no	yes	0	no_start_codon
TX0152	ctg1	-	27	yes	yes	0	ok
TX0153	ctg2	-	6	yes	yes	0	ok
TX0154	ctg2	+	18	yes	yes	1	internal_stop
TX0155	ctg1	-	12	yes	yes	0	ok
TX0156	ctg2	-	12	yes	yes	0	ok
TX0157	ctg2	-	9	no	yes	0	no_start_codon
TX0158	ctg1	-	30	yes	yes	0	ok
TX0159	ctg1	+	36	yes	no	0	no_stop_codon
TX0160	ctg1	+	30	yes	yes	0	ok
TX0161	ctg1	+	6	yes	no	0	no_stop_codon
TX0162	ctg2	+	12	yes	yes	0	ok
TX0163	ctg2	-	33	yes	yes	0	ok
TX0164	ctg1	+	12	yes	yes	0	ok
TX0165	ctg2	-	24	yes	no	0	no_stop_codon
TX0166	ctg2	+	12	yes	yes	0	ok
TX0167	ctg2	-	45	yes	yes	0	ok
TX0168	ctg2	-	18	yes	no	0	no_stop_codon
TX0169	ctg2	+	18	yes	yes	0	ok
TX0170	ctg1	-	6	yes	yes	0	ok
TX0171	ctg2	-	24	no	yes	0	no_start_codon
TX0172	ctg1	-	12	yes	yes	0	ok
TX0173	ctg2	-	30	yes	yes	0	ok
TX0174	ctg1	-	15	yes	yes	0	ok
TX0175	ctg1	+	12	yes	yes	0	ok
TX0176	ctg2	+	12	yes	yes	0	ok
TX0177	ctg2	-	39	yes	yes	0	ok
TX0178	ctg1	-	21	yes	yes	0	ok
TX0179	ctg2	+	39	yes	yes	0	ok
TX0180	ctg1	+	30	yes	yes	0	ok
TX0181	ctg1	+	21	yes	yes	0	ok
TX0182	ctg2	+	15	yes	yes	0	ok
TX0183	ctg1	+	9	yes	no	0	no_stop_codon
TX0184	ctg2	+	39	yes	yes	0	ok
TX0185	ctg1	-	18	yes	yes	0	ok
TX0186	ctg2	+	21	yes	yes	0	ok
TX0187	ctg2	-	36	yes	yes	0	ok
TX0188	ctg1	+	17	yes	no	0	not_multiple_of_three
TX0189	ctg1	-	9	yes	yes	0	ok
TX0190	ctg2	+	15	yes	yes	0	ok
TX0191	ctg1	+	27	yes	yes	0	ok
TX0192	ctg1	+	48	yes	yes	0	ok
TX0193	ctg1	+	15	yes	yes	1	internal_stop
TX0194	ctg1	-	33	yes	yes	0	ok
TX0195	ctg1	-	24	yes	yes	0	ok
TX0196	ctg1	-	23	yes	no	0	not_multiple_of_three
TX0197	ctg1	+	33	yes	yes	0	ok
TX0198	ctg2	-	9	yes	yes	0	ok
TX0199	ctg2	-	18	yes	yes	0	ok
TX0200	ctg2	+	33	yes	yes	0	ok
TX0201	ctg1	-	30	yes	yes	1	internal_stop
TX0202	ctg2	+	30	yes	yes	0	ok
TX0203	ctg1	+	15	yes	yes	0	ok
TX0204	ctg1	-	36	yes	yes	0	ok
TX0205	ctg2	+	36	yes	yes	0	ok
TX0206	ctg1	+	30	yes	yes	0	ok
TX0207	ctg1	+	21	yes	yes	0	ok
TX0208	ctg1	-	5	yes	no	0	not_multiple_of_three
TX0209	ctg2	+	36	yes	yes	0	ok
TX0210	ctg1	+	12	yes	yes	0	ok
TX0211	ctg2	-	33	yes	yes	0	ok
TX0212	ctg1	-	18	yes	yes	0	ok
TX0213	ctg1	+	36	yes	yes	0	ok
TX0214	ctg2	-	9	no	yes	0	no_start_codon
TX0215	ctg2	-	14	yes	no	0	not_multiple_of_three
TX0216	ctg1	-	36	yes	yes	0	ok
TX0217	ctg1	+	27	no	yes	0	no_start_codon
TX0218	ctg2	+	33	yes	yes	0	ok
TX0219	ctg2	+	33	yes	yes	0	ok
TX0220	ctg2	+	15	yes	yes	1	internal_stop
TX0221	ctg1	-	6	yes	yes	0	ok
TX0222	ctg2	+	30	yes	yes	1	internal_stop
TX0223	ctg2	-	18	yes	yes	0	ok
TX0224	ctg2	+	21	yes	no	0	no_stop_codon
TX0225	ctg1	+	6	yes	yes	0	ok
TX0226	ctg1	-	9	yes	yes	0	ok
TX0227	ctg2	-	24	yes	yes	0	ok
TX0228	ctg2	+	36	yes	yes	0	ok
TX0229	ctg2	+	24	yes	yes	0	ok
TX0230	ctg2	+	33	yes	yes	0	ok
TX0231	ctg1	+	27	no	yes	0	no_start_codon
TX0232	ctg1	-	36	yes	yes	0	ok
TX0233	ctg2	-	24	no	yes	0	no_start_codon
TX0234	ctg1	-	48	yes	no	0	no_stop_codon
TX0235	ctg1	+	18	yes	yes	0	ok
TX0236	ctg1	-	9	no	yes	0	no_start_codon
TX0237	ctg2	-	15	yes	yes	0	ok
TX0238	ctg1	+	44	yes	no	0	not_multiple_of_three
TX0239	ctg2	+	24	yes	yes	0	ok
TX0240	ctg1	-	18	yes	yes	0	ok
TX0241	ctg2	-	42	yes	yes	1	internal_stop
TX0242	ctg2	-	27	yes	yes	1	internal_stop
TX0243	ctg2	-	30	yes	yes	1	internal_stop
TX0244	ctg1	+	18	yes	yes	0	ok
TX0245	ctg2	-	12	yes	no	0	no_stop_codon
TX0246	ctg1	-	9	yes	yes	0	ok
TX0247	ctg2	+	18	yes	yes	0	ok
TX0248	ctg1	+	30	yes	yes	0	ok
TX0249	ctg2	-	6	yes	no	0	no_stop_codon
TX0250	ctg1	-	33	yes	yes	1	internal_stop
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
