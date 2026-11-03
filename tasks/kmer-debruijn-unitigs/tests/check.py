#!/usr/bin/env python3
"""Grader for kmer-debruijn-unitigs.

The expected answer is embedded here rather than mounted from ../gold: Harbor
uploads tests/ only at verification time, so nothing in this file is visible to
the agent while it works.
"""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/unitigs.tsv")

EXPECTED = """\
unitig_id	length	n_kmers	sequence
unitig001	319	299	CTACCAAAGCCACGGCTAGAAAGGCTAGTATGACTGGGACAGTATCCGTGCGAACTCCAGCATGGATATTTAAAGACTAATTGATCGGGATTGGCTCATAGTCACATTGGCAACTCTATGTTCTCGGCGGACTAACTAACCTGACTTATCTTAGAAGCCTCGTGACGGAGTGCATCTCTAGCTAATTTCCTCGACAGGCTACCAGTGTATGTGGTCGTCCCGAAACCCCAGGTATTAGCGTAGTTTTCTAAGTAATCTTGCGCTGAGTACTTACCGCTGATCGTCGGATTTCACGTCTATCGACCGATGGCAAGTCACT
unitig002	298	278	GGCGCCGGATCTGTAATTAGCCTTTGAGTAGTGAAGGTCCATTAATATGGTTTAGCAGTCTATTACGGCGCTACGCACGAACGGTAAAGTTATAGCGAACGGGGCCCGCTGCCCATAAGCACTTGGCGATCCCCGTAGGTCCGTCAAGGTATGATCACTATGGAAGATGACCAATTTATGGACCGTGCGTGGAAGCGGAACACGTTCCGAGTGCATGGCGTCCTGGCGGGTATCTTCAGGTCTGCGTTATAGCCGGAAACTGGTACATTAGCGACTCCCGGCTTTCTAAGCTACTACT
unitig003	287	267	GGCGCCGGATCTGTAATTAGAGAACCGAGGCAAGCGGATGTGTCTTATCGCGTGATTCGCAATTTGGCCGGCGGATCACTCACGGTTTCGGCGGTTCACCACCGCATGGTCGCGCTGTGTTTGCACTTTGATCGTGAACGCGACCTGTGGACGTTTCACTAGTCCGTGTCGTCGTCGGGGAGGTGGCGAAAATTGTTTCTGGCGGGCCACTCCCCTGAACGTCGACCATGTTACTTTCACACCCATAGGCCGACTATTAGTGCAGTCTCGACCGATGGCAAGTCACT
unitig004	43	23	TCGACCGATGGCAAGTCACTCTCGGCGCCGGATCTGTAATTAG
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
