#!/usr/bin/env python3
"""Grader for region-extract.

Checks that every output read overlaps 22:16000000-17000000 and that
the output read-name set matches the gold set exactly.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

OUT_BAM = Path("/app/output/region_reads.bam")
GOLD_NAMES = Path("/gold/region_read_names.txt")
REGION = ("22", 16_000_000, 17_000_000)


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

if subprocess.run(["samtools", "quickcheck", str(OUT_BAM)]).returncode != 0:
    fail("samtools quickcheck failed")

# Verify every output read overlaps the region
view = run(["samtools", "view", str(OUT_BAM)])
out_names: set[str] = set()
for line in view.splitlines():
    if not line:
        continue
    cols = line.split("\t")
    name, rname, pos = cols[0], cols[2], int(cols[3])
    if rname != REGION[0]:
        fail(f"read {name} on wrong reference {rname}")
    # position is 1-based leftmost; conservative overlap check
    if pos < 1 or pos > REGION[2]:
        fail(f"read {name} pos {pos} outside region end {REGION[2]}")
    out_names.add(name)

gold_names = set(GOLD_NAMES.read_text().split())
if out_names != gold_names:
    extra = out_names - gold_names
    missing = gold_names - out_names
    fail(
        f"read-name set mismatch "
        f"(extra={len(extra)}, missing={len(missing)})"
    )

print(f"ok: {len(out_names)} reads in region {REGION[0]}:{REGION[1]}-{REGION[2]}")
sys.exit(0)
