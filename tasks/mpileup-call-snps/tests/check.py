#!/usr/bin/env python3
"""Grader for mpileup-call-snps (Pattern D: bcftools isec, exact match)."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

OUT = Path("/app/output/calls.vcf.gz")
TBI = Path("/app/output/calls.vcf.gz.tbi")
GOLD = Path("/gold/calls.vcf.gz")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


for p in (OUT, TBI):
    if not p.is_file():
        fail(f"missing {p}")

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    r = subprocess.run(
        ["bcftools", "isec", "-p", str(tmp), "-Oz", str(OUT), str(GOLD)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        fail(f"bcftools isec failed: {r.stderr}")

    def n(p):
        return int(subprocess.check_output(
            f"bcftools view -H {p} | wc -l", shell=True, text=True
        ).strip())

    extra = n(tmp / "0000.vcf.gz")
    missing = n(tmp / "0001.vcf.gz")

if extra or missing:
    fail(f"record set mismatch: extra={extra} missing={missing}")

# Enforce SNV-only
for line in subprocess.check_output(
    ["bcftools", "view", "-H", str(OUT)], text=True
).splitlines():
    if not line:
        continue
    cols = line.split("\t")
    ref, alt = cols[3], cols[4]
    if len(ref) != 1 or len(alt) != 1:
        fail(f"non-SNV in calls.vcf.gz: REF={ref} ALT={alt}")

print("ok: mpileup+call output exactly matches gold (SNP-only)")
sys.exit(0)
