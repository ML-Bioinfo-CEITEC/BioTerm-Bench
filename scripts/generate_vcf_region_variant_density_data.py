#!/usr/bin/env python3
"""Generate a bgzipped VCF + BED and the per-interval density gold table.

Writes:
  /out/data/variants.vcf.gz
  /out/data/variants.vcf.gz.tbi
  /out/data/regions.bed
  /out/gold/density.tsv
"""
from __future__ import annotations

import random
import shutil
import subprocess
from pathlib import Path

SEED = 20260418
VCF = Path("/out/data/variants.vcf.gz")
BED = Path("/out/data/regions.bed")
GOLD = Path("/out/gold/density.tsv")

CONTIGS = [("chr1", 50_000), ("chr2", 40_000), ("chr3", 30_000)]
N_VARIANTS = 500
N_INTERVALS = 30


def classify(ref: str, alt: str) -> str | None:
    """Return 'snv', 'indel', or None (ignore)."""
    if alt.startswith("<") or "[" in alt or "]" in alt or alt == "*":
        return None
    bases = set("ACGT")
    if not set(ref.upper()).issubset(bases) or not set(alt.upper()).issubset(bases):
        return None
    if len(ref) == 1 and len(alt) == 1:
        return "snv"
    return "indel"


def main() -> None:
    VCF.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)

    header = [
        "##fileformat=VCFv4.2",
        "##FILTER=<ID=PASS,Description=\"All filters passed\">",
        "##FILTER=<ID=LowQual,Description=\"Low quality\">",
        "##INFO=<ID=DP,Number=1,Type=Integer,Description=\"Depth\">",
        "##ALT=<ID=DEL,Description=\"Deletion\">",
    ]
    for sn, ln in CONTIGS:
        header.append(f"##contig=<ID={sn},length={ln}>")
    header.append("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO")

    variants: list[tuple[str, int, str, str, str]] = []
    # deterministic set of variants
    for _ in range(N_VARIANTS):
        sn, ln = rng.choice(CONTIGS)
        pos = rng.randint(1, ln)
        kind = rng.choices(["snv", "ins", "del", "mnv"], weights=[70, 10, 10, 10])[0]
        ref, alt = "A", "T"
        if kind == "snv":
            ref, alt = rng.sample(list("ACGT"), 2)
        elif kind == "ins":
            ref = rng.choice("ACGT")
            alt = ref + "".join(rng.choices("ACGT", k=rng.randint(1, 4)))
        elif kind == "del":
            base = rng.choice("ACGT")
            deleted = "".join(rng.choices("ACGT", k=rng.randint(1, 4)))
            ref = base + deleted
            alt = base
        elif kind == "mnv":
            n = rng.randint(2, 4)
            ref = "".join(rng.choices("ACGT", k=n))
            alt = "".join(rng.choices("ACGT", k=n))
        filt = rng.choices(["PASS", "LowQual"], weights=[8, 1])[0]
        variants.append((sn, pos, ref, alt, filt))

    # Symbolic / star ALT that must be ignored
    for _ in range(15):
        sn, ln = rng.choice(CONTIGS)
        pos = rng.randint(1, ln)
        variants.append((sn, pos, "A", "<DEL>", "PASS"))
    for _ in range(10):
        sn, ln = rng.choice(CONTIGS)
        pos = rng.randint(1, ln)
        variants.append((sn, pos, "A", "*", "PASS"))

    # Multi-allelic records (combine a SNV + an indel ALT); each ALT counted.
    multi_allelic = []
    for _ in range(20):
        sn, ln = rng.choice(CONTIGS)
        pos = rng.randint(1, ln)
        ref = "A"
        alts = "G,AT"  # SNV + insertion; the insertion classifies as indel
        variants.append((sn, pos, ref, alts, "PASS"))
        multi_allelic.append((sn, pos, ref, alts))

    # Sort
    chrom_order = {sn: i for i, (sn, _) in enumerate(CONTIGS)}
    variants.sort(key=lambda v: (chrom_order[v[0]], v[1]))

    rows = [
        f"{sn}\t{pos}\t.\t{ref}\t{alt}\t30.0\t{filt}\tDP=20"
        for sn, pos, ref, alt, filt in variants
    ]

    plain = Path("/tmp/variants.vcf")
    plain.write_text("\n".join(header + rows) + "\n")
    subprocess.check_call(["bash", "-c", f"bgzip -f {plain} && tabix -p vcf {plain}.gz"])
    shutil.move(f"{plain}.gz", VCF)
    shutil.move(f"{plain}.gz.tbi", str(VCF) + ".tbi")

    # Generate intervals (overlaps allowed). Randomly pick contig, start, width.
    intervals: list[tuple[str, int, int]] = []
    for _ in range(N_INTERVALS):
        sn, ln = rng.choice(CONTIGS)
        width = rng.randint(1_000, 8_000)
        start = rng.randint(0, ln - width)
        end = start + width
        intervals.append((sn, start, end))

    BED.write_text(
        "\n".join(f"{sn}\t{s}\t{e}" for sn, s, e in intervals) + "\n"
    )

    # Build gold
    # Expand each (CHROM, POS, REF, ALT) into per-allele entries
    exploded: list[tuple[str, int, str]] = []  # (chrom, pos, kind)
    for sn, pos, ref, alts, _filt in variants:
        for alt in alts.split(","):
            kind = classify(ref, alt)
            if kind is None:
                continue
            exploded.append((sn, pos, kind))

    gold_lines = ["chrom\tstart\tend\tn_snv\tn_indel\tdensity_per_kb"]
    for sn, s, e in intervals:
        n_snv = sum(
            1 for (c, p, k) in exploded if c == sn and s + 1 <= p <= e and k == "snv"
        )
        n_indel = sum(
            1 for (c, p, k) in exploded if c == sn and s + 1 <= p <= e and k == "indel"
        )
        density = 1000.0 * (n_snv + n_indel) / (e - s)
        gold_lines.append(f"{sn}\t{s}\t{e}\t{n_snv}\t{n_indel}\t{density:.4f}")

    GOLD.write_text("\n".join(gold_lines) + "\n")
    print(f"wrote {VCF}, {BED}, {GOLD}; {len(intervals)} intervals, {len(exploded)} counted ALT records")


if __name__ == "__main__":
    main()
