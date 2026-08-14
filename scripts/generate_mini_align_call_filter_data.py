#!/usr/bin/env python3
"""Generate fixtures for mini-align-call-filter.

Writes under ``$BIOTERM_OUT_ROOT`` (default: ``/out``):
  data/ref.fa
  data/ref.fa.fai
  data/reads_1.fastq.gz
  data/reads_2.fastq.gz
  data/targets.bed
  gold/final.vcf.gz
  gold/final.vcf.gz.tbi
"""
from __future__ import annotations

import gzip
import os
import random
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

SEED = 20260812
CHROM = "chrMini"
REF_LEN = 6500
READ_LEN = 90
FRAG_LEN = 180
FRAGS_PER_HAP = 420
BOOST_FRAGS_PER_HAP = 36
LINE_LEN = 60
BASES = "ACGT"
COMP = str.maketrans("ACGT", "TGCA")


@dataclass(frozen=True)
class Variant:
    pos: int
    ref: str
    alt: str
    haplotypes: tuple[int, ...]


def out_root() -> Path:
    return Path(os.environ.get("BIOTERM_OUT_ROOT", "/out"))


def revcomp(seq: str) -> str:
    return seq.translate(COMP)[::-1]


def rand_seq(n: int, rng: random.Random) -> str:
    return "".join(rng.choice(BASES) for _ in range(n))


def overwrite(seq: str, pos1: int, repl: str) -> str:
    start = pos1 - 1
    return seq[:start] + repl + seq[start + len(repl):]


def write_fasta(path: Path, name: str, seq: str) -> None:
    with path.open("w") as fh:
        fh.write(f">{name}\n")
        for i in range(0, len(seq), LINE_LEN):
            fh.write(seq[i:i + LINE_LEN] + "\n")


def write_fai(path: Path, name: str, seq: str) -> None:
    header = f">{name}\n"
    offset = len(header.encode())
    path.write_text(f"{name}\t{len(seq)}\t{offset}\t{LINE_LEN}\t{LINE_LEN + 1}\n")


def apply_variants(ref_seq: str, variants: list[Variant], hap: int) -> str:
    seq = ref_seq
    for var in sorted(variants, key=lambda v: v.pos, reverse=True):
        if hap not in var.haplotypes:
            continue
        start = var.pos - 1
        assert seq[start:start + len(var.ref)] == var.ref
        seq = seq[:start] + var.alt + seq[start + len(var.ref):]
    return seq


def build_variants(ref_seq: str) -> list[Variant]:
    def alt_not_ref(pos: int, preferred: str) -> str:
        ref = ref_seq[pos - 1]
        if preferred != ref:
            return preferred
        for base in BASES:
            if base != ref:
                return base
        raise AssertionError("unreachable")

    def snv(pos: int, alt: str, haplotypes: tuple[int, ...]) -> Variant:
        ref = ref_seq[pos - 1]
        alt = alt_not_ref(pos, alt)
        return Variant(pos=pos, ref=ref, alt=alt, haplotypes=haplotypes)

    return [
        snv(1021, "G", (2,)),
        snv(1450, "T", (1,)),
        snv(2730, "T", (1, 2)),
        Variant(pos=3045, ref="CA", alt="C", haplotypes=(1, 2)),
        snv(4321, "A", (1,)),
        snv(5875, "C", (1, 2)),  # outside targets; should be filtered away
    ]


def write_fastqs(
    path_r1: Path,
    path_r2: Path,
    hap_seqs: list[str],
    focus_positions: list[int],
    rng: random.Random,
) -> int:
    total = 0
    with gzip.open(path_r1, "wt") as r1, gzip.open(path_r2, "wt") as r2:
        for hap_idx, seq in enumerate(hap_seqs, start=1):
            max_start = len(seq) - FRAG_LEN
            for frag_idx in range(FRAGS_PER_HAP):
                start = rng.randint(0, max_start)
                frag = seq[start:start + FRAG_LEN]
                read1 = frag[:READ_LEN]
                read2 = revcomp(frag[-READ_LEN:])
                name = f"hap{hap_idx}_{frag_idx:04d}"
                qual = "I" * READ_LEN
                r1.write(f"@{name}/1\n{read1}\n+\n{qual}\n")
                r2.write(f"@{name}/2\n{read2}\n+\n{qual}\n")
                total += 1
            for focus_idx, pos in enumerate(focus_positions, start=1):
                low = max(0, pos - READ_LEN)
                high = min(max_start, pos - 20)
                high = max(high, low)
                for rep in range(BOOST_FRAGS_PER_HAP):
                    start = rng.randint(low, high)
                    frag = seq[start:start + FRAG_LEN]
                    read1 = frag[:READ_LEN]
                    read2 = revcomp(frag[-READ_LEN:])
                    name = f"hap{hap_idx}_focus{focus_idx}_{rep:03d}"
                    qual = "I" * READ_LEN
                    r1.write(f"@{name}/1\n{read1}\n+\n{qual}\n")
                    r2.write(f"@{name}/2\n{read2}\n+\n{qual}\n")
                    total += 1
    return total


def bgzip_and_index(src_vcf: Path, dst_vcf: Path) -> None:
    subprocess.check_call(["bgzip", "-f", str(src_vcf)])
    gz = src_vcf.with_suffix(src_vcf.suffix + ".gz")
    subprocess.check_call(["tabix", "-f", "-p", "vcf", str(gz)])
    shutil.move(gz, dst_vcf)
    shutil.move(Path(str(gz) + ".tbi"), Path(str(dst_vcf) + ".tbi"))


def main() -> None:
    root = out_root()
    data_dir = root / "data"
    gold_dir = root / "gold"
    data_dir.mkdir(parents=True, exist_ok=True)
    gold_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)
    ref_seq = rand_seq(REF_LEN, rng)
    ref_seq = overwrite(ref_seq, 3044, "CCAAAAAGGGTT")
    variants = build_variants(ref_seq)
    hap1 = apply_variants(ref_seq, variants, 1)
    hap2 = apply_variants(ref_seq, variants, 2)

    write_fasta(data_dir / "ref.fa", CHROM, ref_seq)
    write_fai(data_dir / "ref.fa.fai", CHROM, ref_seq)

    targets = [
        (CHROM, 900, 1800),
        (CHROM, 2500, 3400),
        (CHROM, 4200, 5200),
    ]
    (data_dir / "targets.bed").write_text(
        "\n".join(f"{chrom}\t{start}\t{end}" for chrom, start, end in targets) + "\n"
    )

    focus_positions = [var.pos for var in variants if var.pos <= 5200]
    n_pairs = write_fastqs(
        data_dir / "reads_1.fastq.gz",
        data_dir / "reads_2.fastq.gz",
        [hap1, hap2],
        focus_positions,
        rng,
    )

    def in_targets(pos: int) -> bool:
        return any(start < pos <= end for _chrom, start, end in targets)

    gold_records = [
        var for var in sorted(variants, key=lambda v: v.pos)
        if in_targets(var.pos)
    ]

    vcf_lines = [
        "##fileformat=VCFv4.2",
        f"##contig=<ID={CHROM},length={REF_LEN}>",
        '##FILTER=<ID=PASS,Description="All filters passed">',
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
    ]
    for var in gold_records:
        vcf_lines.append(
            f"{CHROM}\t{var.pos}\t.\t{var.ref}\t{var.alt}\t60\tPASS\t."
        )
    tmp_vcf = Path("/tmp/mini_align_call_filter_gold.vcf")
    tmp_vcf.write_text("\n".join(vcf_lines) + "\n")
    bgzip_and_index(tmp_vcf, gold_dir / "final.vcf.gz")

    print(
        f"wrote {data_dir} and {gold_dir}; "
        f"{len(gold_records)} in-target variants, {n_pairs} read pairs"
    )


if __name__ == "__main__":
    main()
