#!/usr/bin/env python3
"""Generate synthetic BAM with diverse flags + gold metrics for flagstat-report.

Deterministic: seeded RNG. Creates:
  /out/data/reads.bam
  /out/gold/metrics.tsv

Composition:
  - 200 paired reads, properly paired
  - 40  paired reads, not-properly-paired
  - 20  unmapped (paired)
  - 60  supplementary alignments (flag 2048)
  - 40  duplicate-flagged primary reads (flag 1024)
"""
from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path

import pysam

REF = "/opt/references/virus/sars_cov_2.fa.gz"
SAM_PATH = Path("/tmp/reads.sam")
BAM_PATH = Path("/out/data/reads.bam")
GOLD = Path("/out/gold/metrics.tsv")

SEED = 20250418
READ_LEN = 80
INSERT = 200


def sam_record(name, flag, rname, pos, seq, rnext="=", pnext=0, tlen=0):
    qual = "I" * len(seq)
    return (
        f"{name}\t{flag}\t{rname}\t{pos}\t60\t{len(seq)}M\t{rnext}\t{pnext}\t{tlen}"
        f"\t{seq}\t{qual}\n"
    )


def main() -> None:
    rng = random.Random(SEED)
    fa = pysam.FastaFile(REF)
    rname = fa.references[0]
    reflen = fa.get_reference_length(rname)

    def grab_seq(p):
        s = fa.fetch(rname, p, p + READ_LEN).upper()
        return s.replace("N", "A")

    BAM_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    SAM_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "@HD\tVN:1.6\tSO:unsorted\n",
        f"@SQ\tSN:{rname}\tLN:{reflen}\n",
        "@PG\tID:bioterm-bench\tPN:bioterm-bench\tVN:0.1\n",
    ]

    def gen_proper_pair(i: int):
        pos1 = rng.randint(0, reflen - INSERT - READ_LEN - 1)
        pos2 = pos1 + INSERT - READ_LEN
        seq1 = grab_seq(pos1)
        seq2 = grab_seq(pos2)
        tlen = INSERT
        # flags: paired(1) + proper(2) + mate_reverse(32 for R1) + read#
        lines.append(sam_record(f"pp_{i:04d}", 99, rname, pos1 + 1, seq1,
                                rnext="=", pnext=pos2 + 1, tlen=tlen))
        lines.append(sam_record(f"pp_{i:04d}", 147, rname, pos2 + 1, seq2,
                                rnext="=", pnext=pos1 + 1, tlen=-tlen))

    def gen_bad_pair(i: int):
        pos1 = rng.randint(0, reflen - READ_LEN - 1)
        pos2 = rng.randint(0, reflen - READ_LEN - 1)
        seq1 = grab_seq(pos1)
        seq2 = grab_seq(pos2)
        # paired(1) but not proper(2): flags 97, 145
        lines.append(sam_record(f"bp_{i:04d}", 97, rname, pos1 + 1, seq1,
                                rnext="=", pnext=pos2 + 1, tlen=0))
        lines.append(sam_record(f"bp_{i:04d}", 145, rname, pos2 + 1, seq2,
                                rnext="=", pnext=pos1 + 1, tlen=0))

    def gen_unmapped_paired(i: int):
        # paired(1) + read_unmapped(4) + mate_unmapped(8) + read#
        lines.append(sam_record(f"um_{i:04d}", 77, "*", 0,
                                grab_seq(0), rnext="*", pnext=0, tlen=0))
        lines.append(sam_record(f"um_{i:04d}", 141, "*", 0,
                                grab_seq(0), rnext="*", pnext=0, tlen=0))

    def gen_supp(i: int):
        pos = rng.randint(0, reflen - READ_LEN - 1)
        seq = grab_seq(pos)
        # supplementary(2048) + paired(1) + other normal flags
        lines.append(sam_record(f"sp_{i:04d}", 2113, rname, pos + 1, seq))

    def gen_dup(i: int):
        pos = rng.randint(0, reflen - READ_LEN - 1)
        seq = grab_seq(pos)
        # paired(1) + proper(2) + duplicate(1024) -- also counts as mapped+paired
        lines.append(sam_record(f"du_{i:04d}", 1123, rname, pos + 1, seq,
                                rnext="=", pnext=pos + 1, tlen=0))

    for i in range(100):
        gen_proper_pair(i)        # 200 reads (paired, proper, mapped)
    for i in range(20):
        gen_bad_pair(i)           # 40 reads (paired, not proper, mapped)
    for i in range(10):
        gen_unmapped_paired(i)    # 20 reads (paired, unmapped)
    for i in range(60):
        gen_supp(i)               # 60 supplementary
    for i in range(40):
        gen_dup(i)                # 40 duplicates (paired/proper/mapped)

    with SAM_PATH.open("w") as fh:
        fh.writelines(lines)

    subprocess.check_call(
        ["samtools", "sort", "-@", "2", "-O", "BAM", "-o", str(BAM_PATH), str(SAM_PATH)]
    )
    subprocess.check_call(["samtools", "index", str(BAM_PATH)])

    # Compute gold metrics by running samtools flagstat JSON and extracting.
    r = subprocess.run(
        ["samtools", "flagstat", "-O", "json", str(BAM_PATH)],
        check=True, capture_output=True, text=True,
    )
    j = json.loads(r.stdout)
    qc = j["QC-passed reads"]
    rows = {
        "total_reads":     qc["total"],
        "mapped":          qc["mapped"],
        "properly_paired": qc["properly paired"],
        "duplicates":      qc["duplicates"],
        "supplementary":   qc["supplementary"],
    }
    with GOLD.open("w") as fh:
        for k in sorted(rows):
            fh.write(f"{k}\t{rows[k]}\n")

    print(f"wrote {BAM_PATH}, gold metrics:")
    for k in sorted(rows):
        print(f"  {k}\t{rows[k]}")


if __name__ == "__main__":
    main()
