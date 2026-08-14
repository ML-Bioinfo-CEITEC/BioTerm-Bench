#!/usr/bin/env python3
"""Generate a multisample VCF plus QC gold tables."""
from __future__ import annotations

import os
import random
import shutil
import subprocess
import tempfile
from pathlib import Path

SEED = 20260812
OUT_ROOT = Path(os.environ.get("OUT_ROOT", "/out"))
VCF = OUT_ROOT / "data" / "calls.vcf.gz"
PAIRS = OUT_ROOT / "data" / "pairs.tsv"
GOLD_SAMPLE = OUT_ROOT / "gold" / "sample_qc.tsv"
GOLD_PAIR = OUT_ROOT / "gold" / "pair_concordance.tsv"

AUTOSOMES = [str(i) for i in range(1, 23)]
SAMPLES = ["S_A", "S_B", "S_C", "S_D", "S_E", "S_F"]
PAIR_LIST = [("S_A", "S_B"), ("S_A", "S_C"), ("S_D", "S_E"), ("S_E", "S_F")]


def norm_gt(gt: str) -> tuple[str, str] | None:
    gt = gt.replace("|", "/")
    alleles = gt.split("/")
    if len(alleles) != 2 or any(a == "." for a in alleles):
        return None
    return tuple(sorted(alleles))


def dosage(gt: str) -> int | None:
    alleles = norm_gt(gt)
    if alleles is None:
        return None
    return sum(1 for allele in alleles if allele != "0")


def is_het(gt: str) -> bool:
    alleles = norm_gt(gt)
    return alleles is not None and alleles[0] != alleles[1]


def main() -> None:
    VCF.parent.mkdir(parents=True, exist_ok=True)
    GOLD_SAMPLE.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)

    header = [
        "##fileformat=VCFv4.2",
        "##FILTER=<ID=PASS,Description=\"All filters passed\">",
        "##FILTER=<ID=LowQual,Description=\"Low quality\">",
        "##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">",
    ]
    for chrom in AUTOSOMES + ["X", "MT"]:
        header.append(f"##contig=<ID={chrom},length=1000000>")
    header.append("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t" + "\t".join(SAMPLES))

    pos_counter = {chrom: 1000 for chrom in AUTOSOMES + ["X", "MT"]}
    rows: list[str] = []
    eligible_sites: list[list[str]] = []

    def emit(chrom: str, ref: str, alt: str, filt: str, genotypes: list[str]) -> None:
        pos_counter[chrom] += rng.randint(17, 149)
        pos = pos_counter[chrom]
        rows.append(
            f"{chrom}\t{pos}\t.\t{ref}\t{alt}\t50\t{filt}\t.\tGT\t" + "\t".join(genotypes)
        )
        if (
            chrom in AUTOSOMES
            and filt in {"PASS", "."}
            and len(ref) == 1
            and len(alt) == 1
            and ref in "ACGT"
            and alt in "ACGT"
        ):
            eligible_sites.append(genotypes[:])

    for _ in range(140):
        chrom = rng.choice(AUTOSOMES)
        base = rng.choices(["0/0", "0/1", "1/1"], weights=[7, 3, 1])[0]
        if base == "0/0":
            alt_base = "0/1"
        elif base == "0/1":
            alt_base = rng.choice(["0/0", "1/1"])
        else:
            alt_base = "0/1"

        gts = {
            "S_A": base,
            "S_B": base if rng.random() < 0.86 else alt_base,
            "S_C": "./." if rng.random() < 0.22 else rng.choices(["0/0", "0/1", "1/1"], weights=[6, 3, 1])[0],
            "S_D": rng.choices(["0/0", "0/1", "1/1", "./."], weights=[2, 7, 1, 1])[0],
            "S_E": rng.choices(["0/0", "0/1", "1/1", "./."], weights=[8, 1, 1, 1])[0],
            "S_F": rng.choices(["0/0", "0/1", "1/1", "./."], weights=[4, 2, 4, 1])[0],
        }
        # Force structured discordance in one pair cohort.
        if rng.random() < 0.20:
            gts["S_E"] = "0/1"
            gts["S_F"] = "1/1"
        emit(chrom, *rng.sample(list("ACGT"), 2), "PASS", [gts[s] for s in SAMPLES])

    for _ in range(12):
        emit("X", "A", "G", "PASS", ["0/1", "0/1", "0/1", "0/1", "0/0", "0/0"])
    for _ in range(12):
        emit(rng.choice(AUTOSOMES), "C", "T", "LowQual", ["0/1", "0/0", "./.", "0/1", "0/0", "1/1"])

    for _ in range(8):
        chrom = rng.choice(AUTOSOMES)
        pos_counter[chrom] += rng.randint(17, 149)
        pos = pos_counter[chrom]
        rows.append(f"{chrom}\t{pos}\t.\tA\tT,C\t50\tPASS\t.\tGT\t0/1\t0/1\t0/0\t0/1\t0/0\t1/1")
    for _ in range(8):
        emit(rng.choice(AUTOSOMES), "AT", "A", "PASS", ["0/1", "0/1", "0/0", "0/1", "0/0", "1/1"])

    rows.sort(key=lambda row: (0 if row.split("\t")[0].isdigit() else 1, row.split("\t")[0], int(row.split("\t")[1])))

    n_sites = len(eligible_sites)
    sample_rows = ["sample\tn_sites\tn_called\tcall_rate\tn_het\thet_rate"]
    for idx, sample in enumerate(SAMPLES):
        called = [site[idx] for site in eligible_sites if norm_gt(site[idx]) is not None]
        n_called = len(called)
        n_het = sum(1 for gt in called if is_het(gt))
        sample_rows.append(
            f"{sample}\t{n_sites}\t{n_called}\t{(n_called / n_sites if n_sites else 0.0):.4f}\t"
            f"{n_het}\t{(n_het / n_called if n_called else 0.0):.4f}"
        )

    pair_rows = ["sample_a\tsample_b\tn_compared\tconcordance"]
    sample_to_idx = {sample: idx for idx, sample in enumerate(SAMPLES)}
    for a, b in PAIR_LIST:
        ia, ib = sample_to_idx[a], sample_to_idx[b]
        compared = 0
        concordant = 0
        for site in eligible_sites:
            da = dosage(site[ia])
            db = dosage(site[ib])
            if da is None or db is None:
                continue
            compared += 1
            if da == db:
                concordant += 1
        pair_rows.append(
            f"{a}\t{b}\t{compared}\t{(concordant / compared if compared else 0.0):.4f}"
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        plain = Path(tmpdir) / "calls.vcf"
        plain.write_text("\n".join(header + rows) + "\n")
        subprocess.check_call(["bgzip", "-f", str(plain)])
        subprocess.check_call(["tabix", "-f", "-p", "vcf", f"{plain}.gz"])
        shutil.move(f"{plain}.gz", VCF)
        shutil.move(f"{plain}.gz.tbi", str(VCF) + ".tbi")

    PAIRS.write_text("sample_a\tsample_b\n" + "\n".join(f"{a}\t{b}" for a, b in PAIR_LIST) + "\n")
    GOLD_SAMPLE.write_text("\n".join(sample_rows) + "\n")
    GOLD_PAIR.write_text("\n".join(pair_rows) + "\n")
    print(f"wrote {VCF}, {PAIRS}, {GOLD_SAMPLE}, {GOLD_PAIR}")


if __name__ == "__main__":
    main()
