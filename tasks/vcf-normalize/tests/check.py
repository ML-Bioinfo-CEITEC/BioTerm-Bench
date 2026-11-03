#!/usr/bin/env python3
"""Grader for vcf-normalize (Pattern D: bcftools isec)."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

OUT = Path("/app/output/norm.vcf.gz")
TBI = Path("/app/output/norm.vcf.gz.tbi")
GOLD = Path("/tests/gold/norm.vcf.gz")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")
if not TBI.is_file():
    fail(f"missing tabix index {TBI}")

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    r = subprocess.run(
        ["bcftools", "isec", "-p", str(tmp), "-Oz", str(OUT), str(GOLD)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        fail(f"bcftools isec failed: {r.stderr}")

    def n(p: Path) -> int:
        out = subprocess.check_output(
            f"bcftools view -H {p} | wc -l", shell=True, text=True
        )
        return int(out.strip())

    extra = n(tmp / "0000.vcf.gz")
    missing = n(tmp / "0001.vcf.gz")

if extra or missing:
    fail(f"record set mismatch: extra={extra} missing={missing}")

# Confirm every output record is mono-allelic (split happened).
r = subprocess.check_output(
    ["bcftools", "view", "-H", str(OUT)], text=True
)
for lineno, line in enumerate(r.splitlines(), 1):
    if not line:
        continue
    alts = line.split("\t")[4]
    if "," in alts:
        fail(f"line {lineno}: multi-allelic record ALT={alts} not split")

print("ok: normalized VCF matches gold and is fully split")
sys.exit(0)
