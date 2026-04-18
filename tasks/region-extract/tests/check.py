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

# Output header must declare coordinate sort
header = run(["samtools", "view", "-H", str(OUT_BAM)])
if "SO:coordinate" not in header:
    fail("output BAM header does not declare SO:coordinate")

# Verify every output read is on the right chromosome
view = run(["samtools", "view", str(OUT_BAM)])
out_names: list[str] = []
prev_pos = -1
for line in view.splitlines():
    if not line:
        continue
    cols = line.split("\t")
    name, rname, pos = cols[0], cols[2], int(cols[3])
    if rname != REGION[0]:
        fail(f"read {name} on wrong reference {rname}")
    if pos < prev_pos:
        fail(f"reads not coordinate-sorted: {pos} < previous {prev_pos}")
    prev_pos = pos
    out_names.append(name)

gold_names = GOLD_NAMES.read_text().split()

if sorted(out_names) != sorted(gold_names):
    extra = set(out_names) - set(gold_names)
    missing = set(gold_names) - set(out_names)
    fail(
        f"read-name set mismatch "
        f"(extra={len(extra)}, missing={len(missing)})"
    )
if len(out_names) != len(gold_names):
    fail(
        f"read count mismatch: output has {len(out_names)} rows, "
        f"gold has {len(gold_names)} (duplicate records?)"
    )

print(f"ok: {len(out_names)} reads in region "
      f"{REGION[0]}:{REGION[1]}-{REGION[2]}, coordinate-sorted")
sys.exit(0)
