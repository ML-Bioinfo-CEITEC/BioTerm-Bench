#!/usr/bin/env python3
"""Grader for depth-gc-bias-correction.

The expected answer is embedded here rather than mounted from ../gold: Harbor
uploads tests/ only at verification time, so nothing in this file is visible to
the agent while it works.
"""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/flagged_windows.tsv")

EXPECTED = """\
chrom	start	end	gc	raw_depth	corrected_depth	flag
chr1	4000	5000	0.4427	104.68	99.3087	high
chr1	79000	80000	0.5590	10.55	12.2691	low
chr1	89000	90000	0.4968	13.26	12.5032	low
chr1	100000	101000	0.6562	17.87	17.8700	low
chr1	168000	169000	0.5450	90.50	90.9149	high
chr1	201000	202000	0.2888	11.37	18.5744	low
chr1	241000	242000	0.3523	11.56	11.4753	low
chr1	245000	246000	0.7059	9.10	9.1000	low
chr1	259000	260000	0.5151	90.44	90.8546	high
chr1	284000	285000	0.6789	14.19	14.1900	low
chr1	306000	307000	0.4486	13.36	12.6745	low
chr1	346000	347000	0.4898	12.59	11.8714	low
chr1	350000	351000	0.6848	12.13	12.1300	low
chr1	359000	360000	0.4983	12.40	11.6923	low
chr1	366000	367000	0.4419	13.13	12.4563	low
chr1	375000	376000	0.5364	95.95	96.3898	high
chr1	378000	379000	0.6586	15.12	15.1200	low
chr1	396000	397000	0.6566	17.48	17.4800	low
chr1	459000	460000	0.2981	36.09	58.9578	high
chr1	477000	478000	0.6807	10.48	10.4800	low
chr1	526000	527000	0.5039	105.37	105.8530	high
chr1	548000	549000	0.4426	84.90	80.5437	high
chr1	627000	628000	0.5920	76.17	88.5817	high
chr1	631000	632000	0.5650	12.63	14.6880	low
chr1	671000	672000	0.6821	13.37	13.3700	low
chr1	699000	700000	0.4037	13.22	12.5417	low
chr2	37000	38000	0.3217	79.98	91.1488	high
chr2	129000	130000	0.5491	82.79	83.1695	high
chr2	132000	133000	0.3234	11.35	12.9350	low
chr2	163000	164000	0.4831	104.88	98.8941	high
chr2	234000	235000	0.7018	5.27	5.2700	low
chr2	314000	315000	0.5465	84.21	84.5960	high
chr2	326000	327000	0.3731	14.53	14.4235	low
chr2	328000	329000	0.6331	65.36	96.7032	high
chr2	392000	393000	0.4900	83.20	78.4514	high
chr2	537000	538000	0.6659	18.61	18.6100	low
chr2	545000	546000	0.4031	92.34	87.6019	high
chr2	564000	565000	0.4562	85.98	81.0728	high
chr2	569000	570000	0.4811	13.12	12.3712	low
chr2	573000	574000	0.7280	1.51	1.5100	low
chr2	592000	593000	0.5981	10.04	11.6760	low
chr2	601000	602000	0.4396	89.93	85.3156	high
chr2	604000	605000	0.5056	85.45	85.8417	high
chr2	655000	656000	0.2953	7.91	12.9220	low
chr3	3000	4000	0.5716	11.64	13.5367	low
chr3	103000	104000	0.5015	12.04	12.0952	low
chr3	106000	107000	0.4320	90.88	86.2168	high
chr3	146000	147000	0.5589	12.45	14.4787	low
chr3	207000	208000	0.5113	87.46	87.8609	high
chr3	216000	217000	0.4471	13.75	13.0445	low
chr3	218000	219000	0.6971	9.41	9.4100	low
chr3	220000	221000	0.3372	10.20	11.6244	low
chr3	231000	232000	0.4590	14.43	13.6064	low
chr3	239000	240000	0.4932	13.25	12.4938	low
chr3	247000	248000	0.4913	13.76	12.9747	low
chr3	263000	264000	0.3656	13.76	13.6592	low
chr3	293000	294000	0.4609	14.85	14.0024	low
chr3	319000	320000	0.4345	80.72	76.5781	high
chr3	329000	330000	0.7024	7.75	7.7500	low
chr3	367000	368000	0.2500	10.60	17.3165	low
chr3	396000	397000	0.6518	15.87	15.8700	low
chr3	400000	401000	0.6655	13.83	13.8300	low
chr3	463000	464000	0.5074	86.26	86.6554	high
chr3	549000	550000	0.4643	13.23	12.4749	low
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
            if abs(gf - wf) > 0.001:
                fail(f"line {i} column {col}: actual={gv} gold={wv}")
    print("ok")


main()
