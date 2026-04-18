#!/usr/bin/env python3
"""Grader for vcf-split-by-type (Pattern D: bcftools isec on each output)."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

SNPS = Path("/app/output/snps.vcf.gz")
INDELS = Path("/app/output/indels.vcf.gz")
GOLD_SNPS = Path("/gold/snps.vcf.gz")
GOLD_INDELS = Path("/gold/indels.vcf.gz")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def isec_diff(a: Path, b: Path) -> tuple[int, int]:
    """Return (private_to_a, private_to_b) record counts."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        r = subprocess.run(
            ["bcftools", "isec", "-p", str(tmp), "-Oz", str(a), str(b)],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            fail(f"bcftools isec {a.name} vs {b.name} failed: {r.stderr}")

        def n(p):
            return int(subprocess.check_output(
                f"bcftools view -H {p} | wc -l", shell=True, text=True
            ).strip())

        return n(tmp / "0000.vcf.gz"), n(tmp / "0001.vcf.gz")


for p in (SNPS, INDELS, Path(str(SNPS) + ".tbi"), Path(str(INDELS) + ".tbi")):
    if not p.is_file():
        fail(f"missing {p}")

extra, missing = isec_diff(SNPS, GOLD_SNPS)
if extra or missing:
    fail(f"snps.vcf.gz mismatch: extra={extra} missing={missing}")

extra, missing = isec_diff(INDELS, GOLD_INDELS)
if extra or missing:
    fail(f"indels.vcf.gz mismatch: extra={extra} missing={missing}")

# Sanity: every output SNP must be SNV, every indel must be an indel.
for line in subprocess.check_output(
    ["bcftools", "view", "-H", str(SNPS)], text=True
).splitlines():
    if not line:
        continue
    cols = line.split("\t")
    ref, alt = cols[3], cols[4]
    if len(ref) != 1 or len(alt) != 1:
        fail(f"snps.vcf.gz has non-SNV record: REF={ref} ALT={alt}")

for line in subprocess.check_output(
    ["bcftools", "view", "-H", str(INDELS)], text=True
).splitlines():
    if not line:
        continue
    cols = line.split("\t")
    ref, alt = cols[3], cols[4]
    if len(ref) == 1 and len(alt) == 1:
        fail(f"indels.vcf.gz has SNV record: REF={ref} ALT={alt}")

print("ok: snps/indels outputs match gold and honor type constraints")
sys.exit(0)
