#!/usr/bin/env python3
"""Grader for rnaseq-tpm-rpkm-divergence.

The expected answer is embedded here rather than mounted from ../gold: Harbor
uploads tests/ only at verification time, so nothing in this file is visible to
the agent while it works.
"""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/rank_divergence.tsv")

EXPECTED = """\
gene	mean_tpm	mean_rpkm	rank_tpm	rank_rpkm	rank_shift
G0495	248.7459	89.2509	543	500	43
G0614	402.7881	146.2597	425	382	43
G0489	262.9591	92.8486	527	487	40
G0568	263.3532	92.9881	526	486	40
G0688	560.5351	203.3430	345	305	40
G0242	552.8150	198.9978	350	311	39
G0270	400.9829	141.4408	427	391	36
G0168	793.6962	289.8677	263	229	34
G0610	537.7230	194.7553	355	321	34
G0119	294.2810	101.7089	495	462	33
G0384	259.3712	89.9924	531	498	33
G0100	196.9098	69.7560	602	570	32
G0581	758.6986	274.1164	271	239	32
G0717	509.7280	184.0491	365	333	32
G0310	394.9279	139.0883	430	399	31
G0023	501.4593	181.1460	367	337	30
G0053	446.5389	155.6261	399	370	29
G0073	207.3643	71.2692	591	562	29
G0249	791.5383	279.6034	264	235	29
G0608	286.6056	97.9058	500	471	29
G0544	220.2294	78.0465	570	542	28
G0566	239.8209	81.4627	554	526	28
G0633	266.5589	90.6417	523	495	28
G0067	530.6303	184.4476	358	332	26
G0068	409.9273	139.5656	422	396	26
G0445	584.6624	204.7361	328	302	26
G0572	274.2747	93.3739	510	484	26
G0338	556.6977	193.8245	348	323	25
G0504	814.4912	287.9748	257	232	25
G0651	670.6577	239.9021	295	270	25
G0730	469.8224	168.1133	382	357	25
G0043	233.6845	80.3336	556	532	24
G0153	636.1758	221.6335	311	287	24
G0306	335.4829	117.1772	459	435	24
G0356	189.1147	64.6868	613	589	24
G0438	511.5508	179.6846	364	340	24
G0586	620.7282	212.6260	316	292	24
G0603	802.2601	275.0674	261	237	24
G0107	675.5752	197.5158	293	316	23
G0208	586.3696	204.4665	327	304	23
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
