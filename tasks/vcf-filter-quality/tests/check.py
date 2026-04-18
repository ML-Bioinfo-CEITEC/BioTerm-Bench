#!/usr/bin/env python3
"""Grader for vcf-filter-quality (Pattern D: bcftools isec)."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

OUT = Path("/app/output/passed.vcf.gz")
TBI = Path("/app/output/passed.vcf.gz.tbi")
GOLD = Path("/gold/passed.vcf.gz")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")
if not TBI.is_file():
    fail(f"missing tabix index {TBI}")

# isec: counts records private to A (0002), private to B (0003).
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    r = subprocess.run(
        ["bcftools", "isec", "-p", str(tmp), "-Oz", str(OUT), str(GOLD)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        fail(f"bcftools isec failed: {r.stderr}")

    priv_a = tmp / "0000.vcf.gz"   # private to A (output)
    priv_b = tmp / "0001.vcf.gz"   # private to B (gold)

    def n(p):
        out = subprocess.check_output(
            f"bcftools view -H {p} | wc -l", shell=True, text=True
        )
        return int(out.strip())

    extra = n(priv_a)
    missing = n(priv_b)

if extra or missing:
    fail(f"record set mismatch: extra={extra} missing={missing}")

# Confirm every output record actually satisfies the filter
r = subprocess.run(
    ["bcftools", "view", "-H", str(OUT)], capture_output=True, text=True, check=True
)
for lineno, line in enumerate(r.stdout.splitlines(), 1):
    if not line:
        continue
    cols = line.split("\t")
    qual = cols[5]
    try:
        qv = float(qual)
    except ValueError:
        fail(f"line {lineno}: QUAL '{qual}' not numeric")
    if qv < 30:
        fail(f"line {lineno}: QUAL {qv} < 30 slipped through")
    info = cols[7]
    dp = None
    for field in info.split(";"):
        if field.startswith("DP="):
            dp = int(field.split("=")[1])
    if dp is None or dp < 10:
        fail(f"line {lineno}: DP={dp} < 10 slipped through")

print("ok: output matches gold and honors QUAL>=30 AND DP>=10")
sys.exit(0)
