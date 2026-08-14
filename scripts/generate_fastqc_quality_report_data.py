#!/usr/bin/env python3
"""Generate a synthetic gzipped FASTQ + gold QC summary.

Reads are drawn deterministically from the SARS-CoV-2 reference baked
into the base image. Quality scores are synthesised with a gentle 3'
drop so that FastQC's per-base quality module has something meaningful
to report.

Writes:
  /out/data/reads.fastq.gz
  /out/gold/qc_summary.json
"""
from __future__ import annotations

import gzip
import json
import random
import subprocess
import tempfile
from pathlib import Path

import pysam

REF = "/opt/references/virus/sars_cov_2.fa.gz"
DATA = Path("/out/data/reads.fastq.gz")
GOLD = Path("/out/gold/qc_summary.json")

SEED = 20250418
N_READS = 5000
READ_LEN = 100


def qual_for_pos(pos: int) -> int:
    # Start at Q35, drop linearly to Q18 at the last base.
    frac = pos / max(READ_LEN - 1, 1)
    return int(round(35 - 17 * frac))


def main() -> None:
    rng = random.Random(SEED)
    fa = pysam.FastaFile(REF)
    rname = fa.references[0]
    reflen = fa.get_reference_length(rname)

    DATA.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    qual_string = "".join(chr(qual_for_pos(i) + 33) for i in range(READ_LEN))

    with gzip.open(DATA, "wt") as fh:
        for i in range(N_READS):
            pos = rng.randint(0, reflen - READ_LEN - 1)
            seq = fa.fetch(rname, pos, pos + READ_LEN).upper().replace("N", "A")
            fh.write(f"@read_{i:05d}\n{seq}\n+\n{qual_string}\n")

    # Compute gold by running FastQC + the same parsing the task requires.
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.check_call(["fastqc", "-q", "-o", tmp, str(DATA)])
        dirs = list(Path(tmp).glob("*_fastqc"))
        if dirs and dirs[0].is_dir():
            report_dir = dirs[0]
        else:
            zp = next(Path(tmp).glob("*_fastqc.zip"))
            subprocess.check_call(["unzip", "-q", "-d", tmp, str(zp)])
            report_dir = next(Path(tmp).glob("*_fastqc"))
        lines = (report_dir / "fastqc_data.txt").read_text().splitlines()

    def basic(key):
        for line in lines:
            if line.startswith(key + "\t"):
                return line.split("\t", 1)[1].strip()
        raise RuntimeError("missing " + key)

    total = int(basic("Total Sequences"))
    sl = basic("Sequence length")
    if "-" in sl:
        lo, hi = sl.split("-")
        smin, smax = int(lo), int(hi)
    else:
        smin = smax = int(sl)
    gc = int(basic("%GC"))

    in_block = False
    n_bases = n_good = 0
    for line in lines:
        if line.startswith(">>Per base sequence quality"):
            in_block = True
            continue
        if in_block:
            if line.startswith(">>END_MODULE"):
                break
            if line.startswith("#") or not line.strip():
                continue
            mean = float(line.split("\t")[1])
            n_bases += 1
            if mean >= 20.0:
                n_good += 1
    q20_frac = n_good / n_bases if n_bases else 0.0

    gold = {
        "total_sequences":     total,
        "sequence_length_min": smin,
        "sequence_length_max": smax,
        "gc_content":          gc,
        "per_base_q20_frac":   q20_frac,
    }
    GOLD.write_text(json.dumps(gold, sort_keys=True, indent=2) + "\n")
    print("gold:", json.dumps(gold, sort_keys=True))


if __name__ == "__main__":
    main()
