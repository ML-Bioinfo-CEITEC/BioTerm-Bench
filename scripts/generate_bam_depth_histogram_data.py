#!/usr/bin/env python3
"""Generate reads.bam + gold coverage.json for bam-depth-histogram.

Uses the SARS-CoV-2 reference bundled into bioterm-base:v1 and
simulates reads (via pysam DNA sampling + bwa) to get a realistic
depth distribution. Deterministic: seeded RNG.
"""
from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path
from statistics import median

REF = Path("/opt/references/virus/sars_cov_2.fa.gz")
OUT_DATA = Path("/out/data")
OUT_GOLD = Path("/out/gold")

SEED = 20250418
N_READS = 2500
READ_LEN = 150


def run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return r.stdout


def main() -> None:
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    OUT_GOLD.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)

    import pysam
    with pysam.FastaFile(str(REF)) as fa:
        contig = fa.references[0]
        seq = fa.fetch(contig)

    fq = OUT_DATA / "_reads.fq"
    with fq.open("w") as fh:
        for i in range(N_READS):
            # Deliberately concentrate reads in ORF regions (1000..15000)
            # so that we get both covered and uncovered positions.
            start = rng.randint(0, 20000)
            if start + READ_LEN > len(seq):
                start = len(seq) - READ_LEN - 1
            read = seq[start:start + READ_LEN]
            # ~1% substitution error to avoid perfect matches biasing mpileup
            read = list(read)
            for j in range(len(read)):
                if rng.random() < 0.005:
                    read[j] = rng.choice("ACGT".replace(read[j].upper(), ""))
            read = "".join(read)
            qual = "I" * READ_LEN
            fh.write(f"@r{i}\n{read}\n+\n{qual}\n")

    # Align to reference
    sam = OUT_DATA / "_reads.sam"
    with sam.open("w") as out_fh:
        subprocess.run(
            ["bwa", "mem", "-t", "2", str(REF), str(fq)],
            check=True, stdout=out_fh, stderr=subprocess.DEVNULL,
        )

    bam = OUT_DATA / "reads.bam"
    subprocess.run(
        ["samtools", "sort", "-@", "2", "-o", str(bam), str(sam)], check=True
    )
    subprocess.run(["samtools", "index", str(bam)], check=True)

    fq.unlink()
    sam.unlink()

    depth_txt = subprocess.run(
        ["samtools", "depth", "-a", str(bam)],
        check=True, capture_output=True, text=True,
    ).stdout
    depths = [int(l.split("\t")[2]) for l in depth_txt.splitlines() if l]
    n = len(depths)
    covered = sum(1 for d in depths if d >= 1)
    gold = {
        "ref_length":       n,
        "mean_depth":       sum(depths) / n,
        "median_depth":     int(sorted(depths)[(n - 1) // 2]),
        "fraction_covered": covered / n,
        "max_depth":        max(depths),
    }
    with (OUT_GOLD / "coverage.json").open("w") as fh:
        json.dump(gold, fh, indent=2, sort_keys=True)

    print(f"wrote reads.bam ({N_READS} reads, ref_len={n}), gold coverage.json")
    print(f"  mean={gold['mean_depth']:.2f} covered={gold['fraction_covered']:.3f} "
          f"median={gold['median_depth']} max={gold['max_depth']}")


if __name__ == "__main__":
    main()
