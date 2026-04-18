#!/usr/bin/env python3
"""Grader for bam-sort-index.

Pattern A-like file-presence + header/index integrity check.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

OUT_BAM = Path("/app/output/sample.sorted.bam")
OUT_BAI = Path("/app/output/sample.sorted.bam.bai")
IN_SAM  = Path("/app/data/unsorted.sam")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        fail(f"{' '.join(cmd)} exited {r.returncode}: {r.stderr.strip()}")
    return r.stdout


if not OUT_BAM.is_file():
    fail(f"missing output BAM: {OUT_BAM}")
if not OUT_BAI.is_file():
    fail(f"missing output BAI: {OUT_BAI}")

# samtools quickcheck -- detects truncation / bad BAM
r = subprocess.run(["samtools", "quickcheck", str(OUT_BAM)])
if r.returncode != 0:
    fail("samtools quickcheck failed on output BAM")

# Header must declare coordinate sort
header = run(["samtools", "view", "-H", str(OUT_BAM)])
if "SO:coordinate" not in header:
    fail("header does not declare SO:coordinate")

# Index must be readable
run(["samtools", "idxstats", str(OUT_BAM)])

# Record counts must match
n_in  = int(run(["samtools", "view", "-c", str(IN_SAM)]).strip())
n_out = int(run(["samtools", "view", "-c", str(OUT_BAM)]).strip())
if n_in != n_out:
    fail(f"record count mismatch: input={n_in} output={n_out}")

print(f"ok: {n_out} records, coordinate-sorted, indexed")
sys.exit(0)
