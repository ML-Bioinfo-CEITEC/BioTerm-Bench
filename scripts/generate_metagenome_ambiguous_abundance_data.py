#!/usr/bin/env python3
"""Generate exact-match metagenome reads with ambiguous reference hits.

Writes:
  /out/data/references.fa
  /out/data/reads.fastq
  /out/gold/abundance.tsv
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

OUT_DATA = Path("/out/data")
OUT_GOLD = Path("/out/gold")
READ_LEN = 70


def revcomp(seq: str) -> str:
    table = str.maketrans("ACGT", "TGCA")
    return seq.translate(table)[::-1]


def repeat_block(seed: str, n: int) -> str:
    return (seed * ((n // len(seed)) + 1))[:n]


def write_fasta(path: Path, records: list[tuple[str, str]]) -> None:
    with path.open("w") as fh:
        for name, seq in records:
            fh.write(f">{name}\n")
            for i in range(0, len(seq), 80):
                fh.write(seq[i : i + 80] + "\n")


def main() -> None:
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    OUT_GOLD.mkdir(parents=True, exist_ok=True)

    unique_alpha_1 = repeat_block("AACCGGTTGCACTG", 220)
    unique_alpha_2 = repeat_block("TTAAGGCCATGCGT", 210)
    unique_beta_1 = repeat_block("CCGTAAGTTCGGAT", 240)
    unique_beta_2 = repeat_block("GGTACCATTCGAAG", 205)
    unique_gamma_1 = repeat_block("ATGCGTACCGTTAA", 230)
    unique_gamma_2 = repeat_block("CGATTAACCGGTGC", 215)
    shared_all = repeat_block("GCTTAGCGATACCGTA", 190)
    shared_ab = repeat_block("TTGACCGATGGTACCA", 150)
    shared_bg = repeat_block("ACCTGATCGGATTCGA", 140)

    refs = [
        (
            "alpha_ref",
            unique_alpha_1 + shared_all + unique_alpha_2 + shared_ab + repeat_block("AGTCCTGAACGTTA", 175),
        ),
        (
            "beta_ref",
            unique_beta_1 + shared_all + repeat_block("TGACCTTAGGCAAT", 165) + shared_ab + unique_beta_2 + shared_bg,
        ),
        (
            "gamma_ref",
            unique_gamma_1 + shared_all + repeat_block("CATGGTTAACCGGA", 150) + shared_bg + unique_gamma_2,
        ),
    ]
    ref_map = dict(refs)
    write_fasta(OUT_DATA / "references.fa", refs)

    reads: list[tuple[str, str]] = []

    def take(ref_id: str, start: int, n: int, reverse_every: int = 0) -> None:
        seq = ref_map[ref_id]
        for i in range(n):
            frag = seq[start + i * 3 : start + i * 3 + READ_LEN]
            if reverse_every and i % reverse_every == 0:
                frag = revcomp(frag)
            reads.append((f"{ref_id}_{start}_{i}", frag))

    take("alpha_ref", 20, 18, reverse_every=3)
    take("beta_ref", 25, 14, reverse_every=4)
    take("gamma_ref", 30, 12, reverse_every=5)
    take("alpha_ref", len(unique_alpha_1) + len(shared_all) + len(unique_alpha_2) + 8, 12, reverse_every=2)
    take(
        "beta_ref",
        len(unique_beta_1) + len(shared_all) + 165 + len(shared_ab) + len(unique_beta_2) + 6,
        10,
        reverse_every=2,
    )
    take("alpha_ref", len(unique_alpha_1) + 14, 8, reverse_every=2)

    no_hit = repeat_block("AAAACCCCGGGGTTTT", READ_LEN)
    for i in range(6):
        reads.append((f"nohit_{i}", no_hit[i:] + no_hit[:i]))

    with (OUT_DATA / "reads.fastq").open("w") as fh:
        for read_id, seq in reads:
            fh.write(f"@{read_id}\n{seq}\n+\n{'I' * len(seq)}\n")

    unique_counts = defaultdict(int)
    ambiguous_weight = defaultdict(float)
    weighted = defaultdict(float)
    lengths = {rid: len(seq) for rid, seq in refs}

    for _read_id, seq in reads:
        rc = revcomp(seq)
        matches = []
        for ref_id, ref_seq in refs:
            if seq in ref_seq or rc in ref_seq:
                matches.append(ref_id)
        if not matches:
            continue
        if len(matches) == 1:
            unique_counts[matches[0]] += 1
        share = 1.0 / len(matches)
        if len(matches) > 1:
            for ref_id in matches:
                ambiguous_weight[ref_id] += share
        for ref_id in matches:
            weighted[ref_id] += share

    denom = sum(weighted[ref_id] / lengths[ref_id] for ref_id, _ in refs)
    with (OUT_GOLD / "abundance.tsv").open("w") as fh:
        fh.write(
            "reference_id\tlength_bp\tunique_reads\tambiguous_weight\t"
            "weighted_reads\trel_abundance_ppm\n"
        )
        for ref_id, _seq in refs:
            rel = 1e6 * (weighted[ref_id] / lengths[ref_id]) / denom
            fh.write(
                f"{ref_id}\t{lengths[ref_id]}\t{unique_counts[ref_id]}\t"
                f"{ambiguous_weight[ref_id]:.4f}\t{weighted[ref_id]:.4f}\t{rel:.6f}\n"
            )

    print(f"wrote references.fa, reads.fastq and gold abundance.tsv ({len(reads)} reads)")


if __name__ == "__main__":
    main()
