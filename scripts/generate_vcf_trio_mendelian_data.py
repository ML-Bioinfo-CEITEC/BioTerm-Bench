#!/usr/bin/env python3
"""Generate a trio VCF with known Mendelian violations + gold summary.

Writes:
  /out/data/trio.vcf.gz
  /out/data/trio.vcf.gz.tbi
  /out/gold/summary.json
"""
from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path

SEED = 20260418
DATA = Path("/out/data/trio.vcf.gz")
GOLD = Path("/out/gold/summary.json")

GTS = ("0/0", "0/1", "1/1")
AUTO_OK = {"0/0": {"0"}, "0/1": {"0", "1"}, "1/1": {"1"}}


def is_consistent(child: str, father: str, mother: str) -> bool:
    fa = AUTO_OK[father]
    ma = AUTO_OK[mother]
    ca = set(child.replace("|", "/").split("/"))
    for a in fa:
        for b in ma:
            if {a, b} == ca:
                return True
    return False


def main() -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)

    autosomes = [str(i) for i in range(1, 23)]
    sex = ["X", "Y", "MT"]

    header = [
        "##fileformat=VCFv4.2",
        "##FILTER=<ID=PASS,Description=\"All filters passed\">",
        "##FILTER=<ID=LowQual,Description=\"Low quality\">",
        "##INFO=<ID=DP,Number=1,Type=Integer,Description=\"Depth\">",
        "##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">",
    ]
    for c in autosomes + sex:
        header.append(f"##contig=<ID={c},length=100000000>")
    header.append("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tCHILD\tFATHER\tMOTHER")

    rows: list[str] = []
    pos_counter = {c: 1000 for c in autosomes + sex}

    n_sites = 0
    n_viol = 0

    def emit(chrom: str, ref: str, alt: str, filt: str,
             gt_c: str, gt_f: str, gt_m: str) -> None:
        nonlocal n_sites, n_viol
        pos_counter[chrom] += rng.randint(100, 500)
        pos = pos_counter[chrom]
        rows.append(
            f"{chrom}\t{pos}\t.\t{ref}\t{alt}\t50.0\t{filt}\tDP=30\tGT\t"
            f"{gt_c}\t{gt_f}\t{gt_m}"
        )
        # Count only if autosomal, biallelic SNV, PASS, no missing GT
        miss = any(x == "." or "./" in x or ".|." in x or x == "./." for x in
                   (gt_c, gt_f, gt_m))
        if (chrom in autosomes and filt == "PASS" and len(ref) == 1
                and len(alt) == 1 and ref in "ACGT" and alt in "ACGT"
                and not miss):
            n_sites += 1
            if not is_consistent(gt_c, gt_f, gt_m):
                n_viol += 1

    # Compatible autosomal sites (bulk)
    for _ in range(400):
        chrom = rng.choice(autosomes)
        father = rng.choices(GTS, weights=[6, 5, 2])[0]
        mother = rng.choices(GTS, weights=[6, 5, 2])[0]
        # pick a consistent child
        candidates = [c for c in GTS if is_consistent(c, father, mother)]
        child = rng.choice(candidates)
        ref, alt = rng.sample(list("ACGT"), 2)
        emit(chrom, ref, alt, "PASS", child, father, mother)

    # Explicit violations
    for _ in range(25):
        chrom = rng.choice(autosomes)
        while True:
            father = rng.choice(GTS)
            mother = rng.choice(GTS)
            child = rng.choice(GTS)
            if not is_consistent(child, father, mother):
                break
        ref, alt = rng.sample(list("ACGT"), 2)
        emit(chrom, ref, alt, "PASS", child, father, mother)

    # Autosomal PASS but with missing GT (must be ignored)
    for _ in range(30):
        chrom = rng.choice(autosomes)
        fa = rng.choice(GTS)
        mo = rng.choice(GTS)
        ch = "./."  # missing child
        ref, alt = rng.sample(list("ACGT"), 2)
        emit(chrom, ref, alt, "PASS", ch, fa, mo)

    # Autosomal non-PASS (must be ignored) with a violation pattern
    for _ in range(20):
        chrom = rng.choice(autosomes)
        emit(chrom, "A", "T", "LowQual", "1/1", "0/0", "0/0")

    # Sex / MT sites (must be ignored even if PASS)
    for _ in range(15):
        chrom = rng.choice(sex)
        emit(chrom, "C", "G", "PASS", "1/1", "0/0", "0/0")

    # Multi-allelic autosomal PASS (must be ignored — not biallelic)
    for _ in range(10):
        chrom = rng.choice(autosomes)
        pos_counter[chrom] += rng.randint(100, 500)
        pos = pos_counter[chrom]
        rows.append(
            f"{chrom}\t{pos}\t.\tA\tT,C\t50.0\tPASS\tDP=30\tGT\t0/1\t0/0\t0/1"
        )

    # Indels autosomal PASS (must be ignored — not SNV)
    for _ in range(10):
        chrom = rng.choice(autosomes)
        emit(chrom, "AC", "A", "PASS", "0/1", "0/0", "0/1")

    rng.shuffle(rows)

    # Re-sort by (chrom, pos) for a well-formed VCF
    def ck(r: str) -> tuple:
        f = r.split("\t")
        try:
            return (int(f[0]), int(f[1]))
        except ValueError:
            return (10_000 + ord(f[0][0]), int(f[1]))
    rows.sort(key=ck)

    plain = Path("/tmp/trio.vcf")
    plain.write_text("\n".join(header + rows) + "\n")

    subprocess.check_call(["bash", "-c",
        f"bgzip -f {plain} && tabix -p vcf {plain}.gz"])
    import shutil
    shutil.move(f"{plain}.gz", DATA)
    shutil.move(f"{plain}.gz.tbi", str(DATA) + ".tbi")

    rate = round(n_viol / n_sites, 4) if n_sites else 0.0
    gold = {
        "n_sites": n_sites,
        "n_violations": n_viol,
        "violation_rate": rate,
    }
    GOLD.write_text(json.dumps(gold, indent=2, sort_keys=True) + "\n")
    print(f"wrote {DATA} gold={gold}")


if __name__ == "__main__":
    main()
