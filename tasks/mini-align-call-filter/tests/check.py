#!/usr/bin/env python3
"""Grader for mini-align-call-filter (Pattern D)."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

OUT = Path("/app/output/final.vcf.gz")
OUT_TBI = Path("/app/output/final.vcf.gz.tbi")
GOLD = Path("/gold/final.vcf.gz")
TARGETS = Path("/app/data/targets.bed")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def count_records(path: Path) -> int:
    return int(subprocess.check_output(f"bcftools view -H {path} | wc -l", shell=True, text=True).strip())


if not OUT.is_file() or not OUT_TBI.is_file():
    fail("missing final.vcf.gz or index")

for line in subprocess.check_output(["bcftools", "query", "-f", "%CHROM\t%POS\t%FILTER\n", str(OUT)], text=True).splitlines():
    chrom, pos_s, filt = line.split("\t")
    if chrom != "chrMini":
        fail(f"unexpected chromosome {chrom}")
    if filt not in {".", "PASS"}:
        fail(f"filtered record at {chrom}:{pos_s}: {filt}")

with tempfile.TemporaryDirectory() as tmpdir:
    tmp = Path(tmpdir)
    subprocess.check_call(["bcftools", "view", "-R", str(TARGETS), "-Oz", "-o", str(tmp / "inside.vcf.gz"), str(OUT)])
    subprocess.check_call(["tabix", "-f", "-p", "vcf", str(tmp / "inside.vcf.gz")])
    inside = count_records(tmp / "inside.vcf.gz")
    total = count_records(OUT)
    if inside != total:
        fail(f"{total - inside} records fall outside target intervals")

    subprocess.check_call(["bcftools", "isec", "-p", str(tmp / "isec"), "-Oz", str(OUT), str(GOLD)])
    extra = count_records(tmp / "isec" / "0000.vcf.gz")
    missing = count_records(tmp / "isec" / "0001.vcf.gz")
    if extra or missing:
        fail(f"VCF mismatch vs gold: extra={extra} missing={missing}")

print("ok: normalized filtered VCF matches gold")
