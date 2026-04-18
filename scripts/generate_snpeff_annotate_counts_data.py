#!/usr/bin/env python3
"""Generate the snpeff-annotate-counts task data.

This script runs *inside* bioterm-variant:v1 with the host's
build-log/ dir mounted at /work (for the pre-downloaded GenBank file)
and the task dir mounted at /out. It:

  1. Copies the pre-downloaded NC_045512.2 GenBank file into a fresh
     snpeff_db/ tree.
  2. Writes a minimal snpeff.config declaring the SARSCoV2 genome.
  3. Runs `snpEff build -genbank` to produce the binary DB.
  4. Writes a curated 15-variant VCF (mix of HIGH/MODERATE/LOW/
     MODIFIER impacts across S, N, ORF1ab, intergenic).
  5. Runs the oracle annotation + impact count to produce the gold
     impact_counts.json.

Deterministic: the curated VCF positions / alleles are hand-picked,
the GenBank is a fixed NCBI accession frozen at v.2.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

GENBANK_SRC = Path("/work/NC_045512.2.gb")
OUT_DATA = Path("/out/data")
OUT_GOLD = Path("/out/gold")

# Hand-picked SARS-CoV-2 variants. Positions and alleles are chosen
# so that snpEff assigns a healthy mix of impact classes.
VCF_RECORDS = [
    (241,   "C", "T"),  # upstream (MODIFIER)
    (1059,  "C", "T"),  # synonymous / missense in ORF1ab
    (3037,  "C", "T"),  # synonymous (LOW)
    (8782,  "C", "T"),  # synonymous in ORF1ab
    (11083, "G", "T"),  # missense (MODERATE)
    (14408, "C", "T"),  # missense in ORF1ab (MODERATE)
    (17747, "C", "T"),  # missense in ORF1ab
    (17858, "A", "G"),  # missense in ORF1ab
    (18060, "C", "T"),  # synonymous
    (22992, "G", "A"),  # missense in S
    (23403, "A", "G"),  # D614G in S (MODERATE)
    (25563, "G", "T"),  # missense in ORF3a
    (26144, "G", "T"),  # missense in ORF3a
    (28144, "T", "C"),  # missense in ORF8
    (28881, "G", "A"),  # R203K in N (MODERATE)
]

HEADER = [
    "##fileformat=VCFv4.2",
    "##contig=<ID=NC_045512.2,length=29903>",
    "##INFO=<ID=DP,Number=1,Type=Integer,Description=\"Depth\">",
    "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
]


def build_snpeff_db() -> None:
    snp_root = OUT_DATA / "snpeff_db"
    genome_dir = snp_root / "data" / "SARSCoV2"
    genome_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(GENBANK_SRC, genome_dir / "genes.gbk")

    (OUT_DATA / "snpeff.config").write_text(
        "data.dir = ./snpeff_db/data/\n"
        "SARSCoV2.genome : SARS-CoV-2\n"
        "SARSCoV2.chromosomes : NC_045512.2\n"
        "SARSCoV2.NC_045512.2.codonTable : Standard\n"
    )

    subprocess.run(
        [
            "snpEff", "build",
            "-c", str(OUT_DATA / "snpeff.config"),
            "-dataDir", str(snp_root / "data"),
            "-genbank", "-v",
            "SARSCoV2",
        ],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def write_vcf() -> Path:
    vcf = OUT_DATA / "variants.vcf"
    with vcf.open("w") as fh:
        for line in HEADER:
            fh.write(line + "\n")
        for pos, ref, alt in VCF_RECORDS:
            fh.write(f"NC_045512.2\t{pos}\t.\t{ref}\t{alt}\t99\tPASS\tDP=100\n")
    return vcf


def annotate_and_count(vcf: Path) -> dict[str, int]:
    r = subprocess.run(
        [
            "snpEff", "-noStats",
            "-c", str(OUT_DATA / "snpeff.config"),
            "-dataDir", str(OUT_DATA / "snpeff_db" / "data"),
            "SARSCoV2",
            str(vcf),
        ],
        check=True, capture_output=True, text=True,
    )
    impacts = {"HIGH": 0, "MODERATE": 0, "LOW": 0, "MODIFIER": 0}
    total = 0
    for line in r.stdout.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        cols = line.split("\t")
        # snpEff echoes its own command line to stdout; skip any line
        # that doesn't look like a real VCF record (>= 8 tab columns).
        if len(cols) < 8:
            continue
        total += 1
        info = cols[7]
        ann = next((kv[4:] for kv in info.split(";") if kv.startswith("ANN=")), None)
        if ann is None:
            continue
        impact = ann.split(",")[0].split("|")[2]
        if impact in impacts:
            impacts[impact] += 1
    return {**impacts, "total": total}


def main() -> None:
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    OUT_GOLD.mkdir(parents=True, exist_ok=True)

    build_snpeff_db()
    vcf = write_vcf()
    gold = annotate_and_count(vcf)
    with (OUT_GOLD / "impact_counts.json").open("w") as fh:
        json.dump(gold, fh, indent=2, sort_keys=True)
        fh.write("\n")

    print(f"wrote variants.vcf ({len(VCF_RECORDS)} records), "
          f"snpeff_db/, snpeff.config, gold impact_counts.json")
    print(f"  gold: {gold}")


if __name__ == "__main__":
    main()
