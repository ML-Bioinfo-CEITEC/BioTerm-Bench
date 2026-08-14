#!/usr/bin/env python3
"""Generate genome + GTF for CDS reconstruction and translation.

Writes:
  $OUT_DIR/data/genome.fa
  $OUT_DIR/data/annot.gtf
  $OUT_DIR/gold/proteins.tsv
"""
from __future__ import annotations

import os
from pathlib import Path

OUT_ROOT = Path(os.environ.get("OUT_DIR", "/out"))
DATA_DIR = OUT_ROOT / "data"
GOLD_DIR = OUT_ROOT / "gold"
GENOME_PATH = DATA_DIR / "genome.fa"
GTF_PATH = DATA_DIR / "annot.gtf"
GOLD_PATH = GOLD_DIR / "proteins.tsv"


def revcomp(seq: str) -> str:
    table = str.maketrans("ACGT", "TGCA")
    return seq.translate(table)[::-1]


def wrap_fasta(seq: str, width: int = 60) -> str:
    return "\n".join(seq[i:i + width] for i in range(0, len(seq), width))


def attr(**kv: str) -> str:
    return "".join(f'{k} "{v}"; ' for k, v in kv.items()).rstrip()


TRANSCRIPTS = [
    {
        "gene_id": "RTG0001",
        "transcript_id": "RTT0001.1",
        "chrom": "chrGT1",
        "strand": "+",
        "exons": [(100, 123), (200, 219), (300, 317)],
        "cds": [(109, 120), (200, 207), (300, 309)],
        "cds_seq": "ATGGAACTGAACCAGAAACCTGGTTTCGCT",
    },
    {
        "gene_id": "RTG0002",
        "transcript_id": "RTT0002.1",
        "chrom": "chrGT1",
        "strand": "+",
        "exons": [(600, 617), (700, 723)],
        "cds": [(605, 617), (700, 713)],
        "cds_seq": "ATGGTTCATTCTCCAACACGTCAGCTG",
    },
    {
        "gene_id": "RTG0003",
        "transcript_id": "RTT0003.1",
        "chrom": "chrGT2",
        "strand": "-",
        "exons": [(400, 419), (500, 516), (620, 639)],
        "cds": [(405, 412), (500, 507), (626, 633)],
        "cds_seq": "ATGGACTCTTACCGCAAAACAGCT",
    },
    {
        "gene_id": "RTG0004",
        "transcript_id": "RTT0004.1",
        "chrom": "chrGT2",
        "strand": "-",
        "exons": [(900, 918), (1000, 1018)],
        "cds": [(906, 914), (1003, 1011)],
        "cds_seq": "ATGAATCCTCAGCGTTTA",
    },
]

NONCODING = [
    {
        "gene_id": "RTG9999",
        "transcript_id": "RTT9999.1",
        "chrom": "chrGT2",
        "strand": "+",
        "exons": [(1300, 1335), (1400, 1420)],
    }
]

CODON_TABLE = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}


def translate(seq: str) -> str:
    return "".join(CODON_TABLE[seq[i:i + 3]] for i in range(0, len(seq), 3))


def compute_phases(cds_spans: list[tuple[int, int]], strand: str) -> list[int]:
    ordered = cds_spans if strand == "+" else list(reversed(cds_spans))
    phases_5p: list[int] = []
    emitted = 0
    for start, end in ordered:
        phases_5p.append(emitted % 3)
        emitted += end - start + 1
    return phases_5p if strand == "+" else list(reversed(phases_5p))


def place_plus(genome: list[str], spans: list[tuple[int, int]], cds_seq: str) -> None:
    cursor = 0
    for start, end in spans:
        size = end - start + 1
        genome[start - 1:end] = list(cds_seq[cursor:cursor + size])
        cursor += size


def place_minus(genome: list[str], spans: list[tuple[int, int]], cds_seq: str) -> None:
    cursor = 0
    for start, end in spans:
        size = end - start + 1
        chunk = cds_seq[cursor:cursor + size]
        genome[start - 1:end] = list(revcomp(chunk))
        cursor += size


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    genomes = {
        "chrGT1": list(("ACGT" * 600)[:2200]),
        "chrGT2": list(("TGCA" * 600)[:2200]),
    }

    for tx in TRANSCRIPTS:
        spans = tx["cds"]
        if tx["strand"] == "+":
            place_plus(genomes[tx["chrom"]], spans, tx["cds_seq"])
        else:
            place_minus(genomes[tx["chrom"]], spans, tx["cds_seq"])

    with GENOME_PATH.open("w") as fh:
        for chrom, seq_list in genomes.items():
            seq = "".join(seq_list)
            fh.write(f">{chrom}\n{wrap_fasta(seq)}\n")

    gtf_lines: list[str] = []
    for tx in TRANSCRIPTS:
        gene_start = min(s for s, _ in tx["exons"])
        gene_end = max(e for _, e in tx["exons"])
        gtf_lines.append(
            f"{tx['chrom']}\tSIM\tgene\t{gene_start}\t{gene_end}\t.\t{tx['strand']}\t.\t"
            f"{attr(gene_id=tx['gene_id'])}\n"
        )
        gtf_lines.append(
            f"{tx['chrom']}\tSIM\ttranscript\t{gene_start}\t{gene_end}\t.\t{tx['strand']}\t.\t"
            f"{attr(gene_id=tx['gene_id'], transcript_id=tx['transcript_id'])}\n"
        )
        for exon_idx, (start, end) in enumerate(tx["exons"], start=1):
            gtf_lines.append(
                f"{tx['chrom']}\tSIM\texon\t{start}\t{end}\t.\t{tx['strand']}\t.\t"
                f"{attr(gene_id=tx['gene_id'], transcript_id=tx['transcript_id'], exon_number=str(exon_idx))}\n"
            )
        phases = compute_phases(tx["cds"], tx["strand"])
        for (start, end), phase in zip(tx["cds"], phases):
            gtf_lines.append(
                f"{tx['chrom']}\tSIM\tCDS\t{start}\t{end}\t.\t{tx['strand']}\t{phase}\t"
                f"{attr(gene_id=tx['gene_id'], transcript_id=tx['transcript_id'])}\n"
            )

    for tx in NONCODING:
        gene_start = min(s for s, _ in tx["exons"])
        gene_end = max(e for _, e in tx["exons"])
        gtf_lines.append(
            f"{tx['chrom']}\tSIM\tgene\t{gene_start}\t{gene_end}\t.\t{tx['strand']}\t.\t"
            f"{attr(gene_id=tx['gene_id'])}\n"
        )
        gtf_lines.append(
            f"{tx['chrom']}\tSIM\ttranscript\t{gene_start}\t{gene_end}\t.\t{tx['strand']}\t.\t"
            f"{attr(gene_id=tx['gene_id'], transcript_id=tx['transcript_id'])}\n"
        )
        for exon_idx, (start, end) in enumerate(tx["exons"], start=1):
            gtf_lines.append(
                f"{tx['chrom']}\tSIM\texon\t{start}\t{end}\t.\t{tx['strand']}\t.\t"
                f"{attr(gene_id=tx['gene_id'], transcript_id=tx['transcript_id'], exon_number=str(exon_idx))}\n"
            )
    GTF_PATH.write_text("".join(gtf_lines))

    with GOLD_PATH.open("w") as fh:
        fh.write("transcript_id\tgene_id\tstrand\tcds_length\tpeptide_length\tpeptide\n")
        for tx in sorted(TRANSCRIPTS, key=lambda x: x["transcript_id"]):
            peptide = translate(tx["cds_seq"])
            fh.write(
                f"{tx['transcript_id']}\t{tx['gene_id']}\t{tx['strand']}\t{len(tx['cds_seq'])}\t"
                f"{len(peptide)}\t{peptide}\n"
            )
    print(f"wrote {GENOME_PATH}, {GTF_PATH}, {GOLD_PATH}")


if __name__ == "__main__":
    main()
