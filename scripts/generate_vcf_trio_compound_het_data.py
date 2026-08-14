#!/usr/bin/env python3
"""Generate a trio VCF for compound-heterozygous gene discovery.

Writes:
  <OUT_ROOT>/data/trio.vcf.gz
  <OUT_ROOT>/data/trio.vcf.gz.tbi
  <OUT_ROOT>/gold/compound_hets.tsv
"""
from __future__ import annotations

import os
import random
import shutil
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

SEED = 20260812
OUT_ROOT = Path(os.environ.get("OUT_ROOT", "/out"))
DATA = OUT_ROOT / "data" / "trio.vcf.gz"
GOLD = OUT_ROOT / "gold" / "compound_hets.tsv"

AUTOSOMES = [str(i) for i in range(1, 23)]
OTHER_CHROMS = ["X", "Y", "MT"]


def alt_count(gt: str) -> int | None:
    gt = gt.replace("|", "/")
    alleles = gt.split("/")
    if any(a == "." for a in alleles):
        return None
    return sum(1 for a in alleles if a != "0")


def norm_gt(gt: str) -> tuple[str, str] | None:
    gt = gt.replace("|", "/")
    alleles = gt.split("/")
    if len(alleles) != 2 or any(a == "." for a in alleles):
        return None
    return tuple(sorted(alleles))


def is_paternal_hit(child: str, father: str, mother: str) -> bool:
    c = alt_count(child)
    f = alt_count(father)
    m = alt_count(mother)
    return c == 1 and f is not None and f >= 1 and m == 0


def is_maternal_hit(child: str, father: str, mother: str) -> bool:
    c = alt_count(child)
    f = alt_count(father)
    m = alt_count(mother)
    return c == 1 and f == 0 and m is not None and m >= 1


def eligible(chrom: str, ref: str, alt: str, filt: str, child: str, father: str, mother: str) -> bool:
    if chrom not in AUTOSOMES:
        return False
    if filt not in {"PASS", "."}:
        return False
    if len(ref) != 1 or len(alt) != 1 or ref not in "ACGT" or alt not in "ACGT":
        return False
    return all(norm_gt(gt) is not None for gt in (child, father, mother))


def main() -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)

    header = [
        "##fileformat=VCFv4.2",
        "##FILTER=<ID=PASS,Description=\"All filters passed\">",
        "##FILTER=<ID=LowQual,Description=\"Low quality\">",
        "##INFO=<ID=GENE,Number=1,Type=String,Description=\"Gene symbol\">",
        "##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">",
    ]
    for chrom in AUTOSOMES + OTHER_CHROMS:
        header.append(f"##contig=<ID={chrom},length=1000000>")
    header.append("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tCHILD\tFATHER\tMOTHER")

    rows: list[str] = []
    pos_counter = {chrom: 1000 for chrom in AUTOSOMES + OTHER_CHROMS}
    gene_hits: dict[str, dict[str, list[int]]] = defaultdict(lambda: {"paternal": [], "maternal": []})

    def emit(
        chrom: str,
        gene: str,
        ref: str,
        alt: str,
        filt: str,
        child: str,
        father: str,
        mother: str,
    ) -> None:
        pos_counter[chrom] += rng.randint(23, 211)
        pos = pos_counter[chrom]
        rows.append(
            f"{chrom}\t{pos}\t.\t{ref}\t{alt}\t60\t{filt}\tGENE={gene}\tGT\t"
            f"{child}\t{father}\t{mother}"
        )
        if not eligible(chrom, ref, alt, filt, child, father, mother):
            return
        if is_paternal_hit(child, father, mother):
            gene_hits[gene]["paternal"].append(pos)
        if is_maternal_hit(child, father, mother):
            gene_hits[gene]["maternal"].append(pos)

    qualifying = {
        "ABCA7": [("0/1", "0/1", "0/0"), ("0/1", "0/0", "0/1"), ("0/1", "1/1", "0/0")],
        "CFTR": [("0/1", "0/1", "0/0"), ("0/1", "0/0", "1/1")],
        "KMT2D": [("0/1", "0/0", "0/1"), ("0/1", "0/1", "0/0"), ("0/1", "0/0", "0/1")],
        "SCN2A": [("0/1", "0/1", "0/0"), ("0/1", "0/0", "0/1")],
    }
    non_qualifying = {
        "BRCA1": [("0/1", "0/1", "0/0"), ("0/1", "1/1", "0/0")],
        "BRCA2": [("0/1", "0/0", "0/1"), ("0/1", "0/0", "1/1")],
        "APC": [("0/1", "0/1", "0/1"), ("0/1", "0/1", "0/1")],
        "KRAS": [("0/1", "0/1", "0/0"), ("1/1", "0/0", "0/1")],
        "PTEN": [("0/0", "0/1", "0/0"), ("0/1", "0/0", "0/0")],
    }

    for gene, configs in qualifying.items():
        chrom = rng.choice(AUTOSOMES)
        for child, father, mother in configs:
            ref, alt = rng.sample(list("ACGT"), 2)
            emit(chrom, gene, ref, alt, "PASS", child, father, mother)
        emit(chrom, gene, "A", "AT", "PASS", "0/1", "0/1", "0/0")
        emit("X", gene, "C", "T", "PASS", "0/1", "0/0", "0/1")

    for gene, configs in non_qualifying.items():
        chrom = rng.choice(AUTOSOMES)
        for child, father, mother in configs:
            ref, alt = rng.sample(list("ACGT"), 2)
            emit(chrom, gene, ref, alt, "PASS", child, father, mother)

    noise_genes = ["MAP2K1", "NOTCH1", "SMARCA4", "BRAF", "DNMT3A", "NF1", "RB1", "ERBB2"]
    noise_patterns = [
        ("0/0", "0/0", "0/0"),
        ("0/1", "0/1", "0/1"),
        ("1/1", "0/1", "0/1"),
        ("0/1", "0/0", "0/0"),
        ("./.", "0/1", "0/0"),
    ]
    for _ in range(90):
        chrom = rng.choice(AUTOSOMES + OTHER_CHROMS)
        gene = rng.choice(noise_genes)
        child, father, mother = rng.choice(noise_patterns)
        ref, alt = rng.sample(list("ACGT"), 2)
        filt = "PASS" if rng.random() < 0.75 else "LowQual"
        emit(chrom, gene, ref, alt, filt, child, father, mother)

    for _ in range(8):
        chrom = rng.choice(AUTOSOMES)
        pos_counter[chrom] += rng.randint(31, 173)
        pos = pos_counter[chrom]
        rows.append(
            f"{chrom}\t{pos}\t.\tA\tT,C\t60\tPASS\tGENE={rng.choice(noise_genes)}\tGT\t"
            "0/1\t0/0\t0/1"
        )

    rng.shuffle(rows)
    rows.sort(key=lambda row: (0 if row.split("\t")[0].isdigit() else 1, row.split("\t")[0], int(row.split("\t")[1])))

    gold_rows = ["gene\tn_paternal\tn_maternal\tfirst_paternal_pos\tfirst_maternal_pos"]
    for gene in sorted(gene_hits):
        paternal = sorted(gene_hits[gene]["paternal"])
        maternal = sorted(gene_hits[gene]["maternal"])
        if not paternal or not maternal:
            continue
        gold_rows.append(f"{gene}\t{len(paternal)}\t{len(maternal)}\t{paternal[0]}\t{maternal[0]}")

    with tempfile.TemporaryDirectory() as tmpdir:
        plain = Path(tmpdir) / "trio.vcf"
        plain.write_text("\n".join(header + rows) + "\n")
        subprocess.check_call(["bgzip", "-f", str(plain)])
        subprocess.check_call(["tabix", "-f", "-p", "vcf", f"{plain}.gz"])
        shutil.move(f"{plain}.gz", DATA)
        shutil.move(f"{plain}.gz.tbi", str(DATA) + ".tbi")

    GOLD.write_text("\n".join(gold_rows) + "\n")
    print(f"wrote {DATA} and {GOLD}")


if __name__ == "__main__":
    main()
