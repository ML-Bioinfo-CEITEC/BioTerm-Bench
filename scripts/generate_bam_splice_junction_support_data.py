#!/usr/bin/env python3
"""Generate a synthetic BAM + GTF for annotated splice-junction support.

Writes:
  $OUT_DIR/data/annot.gtf
  $OUT_DIR/data/reads.bam
  $OUT_DIR/data/reads.bam.bai
  $OUT_DIR/gold/support.tsv
"""
from __future__ import annotations

import os
import re
import subprocess
from collections import defaultdict
from itertools import pairwise
from pathlib import Path

OUT_ROOT = Path(os.environ.get("OUT_DIR", "/out"))
DATA_DIR = OUT_ROOT / "data"
GOLD_DIR = OUT_ROOT / "gold"
GTF_PATH = DATA_DIR / "annot.gtf"
BAM_PATH = DATA_DIR / "reads.bam"
GOLD_PATH = GOLD_DIR / "support.tsv"

CIGAR_RE = re.compile(r"(\d+)([MIDNSHP=X])")
REF_CONSUMING = set("MDN=X")
QUERY_CONSUMING = set("MIS=X")

TRANSCRIPTS = [
    {
        "gene_id": "SJG0001",
        "transcript_id": "SJT0001.1",
        "chrom": "chrSJ1",
        "strand": "+",
        "exons": [(100, 159), (260, 319), (450, 509)],
    },
    {
        "gene_id": "SJG0002",
        "transcript_id": "SJT0002.1",
        "chrom": "chrSJ1",
        "strand": "-",
        "exons": [(800, 849), (920, 979), (1050, 1119)],
    },
    {
        "gene_id": "SJG0003",
        "transcript_id": "SJT0003.1",
        "chrom": "chrSJ2",
        "strand": "+",
        "exons": [(200, 249), (330, 389)],
    },
    {
        "gene_id": "SJG0004",
        "transcript_id": "SJT0004.1",
        "chrom": "chrSJ2",
        "strand": "+",
        "exons": [(600, 639), (720, 759)],
    },
]

READ_SPECS = [
    ("t1_j1_a", 0, "chrSJ1", 130, "30M100N50M"),
    ("t1_j1_b", 0, "chrSJ1", 132, "28M100N52M"),
    ("t1_j1_c", 0, "chrSJ1", 130, "30M100N50M"),
    ("t1_both", 0, "chrSJ1", 130, "30M100N20M130N30M"),
    ("t1_j2_a", 0, "chrSJ1", 290, "30M130N50M"),
    ("t1_j2_b", 0, "chrSJ1", 288, "32M130N48M"),
    ("t2_both", 0, "chrSJ1", 820, "30M70N20M70N30M"),
    ("t2_j1", 0, "chrSJ1", 950, "30M70N50M"),
    ("t2_j2_a", 0, "chrSJ1", 820, "30M70N50M"),
    ("t2_j2_b", 0, "chrSJ1", 818, "32M70N48M"),
    ("t2_j2_c", 0, "chrSJ1", 820, "30M70N50M"),
    ("t2_j2_d", 0, "chrSJ1", 821, "29M70N51M"),
    ("t3_a", 0, "chrSJ2", 220, "30M80N50M"),
    ("t3_b", 0, "chrSJ2", 218, "32M80N48M"),
    ("t3_c", 0, "chrSJ2", 220, "30M80N50M"),
    ("t3_d", 0, "chrSJ2", 219, "31M80N49M"),
    ("novel_splice", 0, "chrSJ1", 130, "30M90N50M"),
    ("secondary_hit", 256, "chrSJ1", 130, "30M100N50M"),
    ("supp_hit", 2048, "chrSJ2", 220, "30M80N50M"),
    ("plain_match", 0, "chrSJ2", 1000, "80M"),
    ("unmapped", 4, "*", 0, "*"),
]

CONTIG_LENGTHS = {"chrSJ1": 5000, "chrSJ2": 4000}


def attr(**kv: str) -> str:
    return "".join(f'{k} "{v}"; ' for k, v in kv.items()).rstrip()


def cigar_query_len(cigar: str) -> int:
    if cigar == "*":
        return 50
    total = 0
    for size, op in CIGAR_RE.findall(cigar):
        if op in QUERY_CONSUMING:
            total += int(size)
    return total


def junctions_from_cigar(start_1based: int, cigar: str) -> list[tuple[int, int]]:
    ref_pos = start_1based
    out: list[tuple[int, int]] = []
    for size_s, op in CIGAR_RE.findall(cigar):
        size = int(size_s)
        if op == "N":
            intron_start = ref_pos
            intron_end = ref_pos + size - 1
            out.append((intron_start, intron_end))
        if op in REF_CONSUMING:
            ref_pos += size
    return out


def transcript_junction_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for tx in TRANSCRIPTS:
        exons = list(tx["exons"])
        ordered = exons if tx["strand"] == "+" else list(reversed(exons))
        for idx, (left, right) in enumerate(pairwise(ordered), start=1):
            left_end = left[1]
            right_start = right[0]
            rows.append(
                {
                    "gene_id": tx["gene_id"],
                    "transcript_id": tx["transcript_id"],
                    "junction_index": idx,
                    "chrom": tx["chrom"],
                    "strand": tx["strand"],
                    "intron_start": left_end + 1,
                    "intron_end": right_start - 1,
                }
            )
    return rows


def write_gtf() -> None:
    lines: list[str] = []
    for tx in TRANSCRIPTS:
        exons = tx["exons"]
        gene_start = min(s for s, _ in exons)
        gene_end = max(e for _, e in exons)
        lines.append(
            f"{tx['chrom']}\tSIM\tgene\t{gene_start}\t{gene_end}\t.\t{tx['strand']}\t.\t"
            f"{attr(gene_id=tx['gene_id'])}\n"
        )
        lines.append(
            f"{tx['chrom']}\tSIM\ttranscript\t{gene_start}\t{gene_end}\t.\t{tx['strand']}\t.\t"
            f"{attr(gene_id=tx['gene_id'], transcript_id=tx['transcript_id'])}\n"
        )
        for exon_idx, (start, end) in enumerate(exons, start=1):
            lines.append(
                f"{tx['chrom']}\tSIM\texon\t{start}\t{end}\t.\t{tx['strand']}\t.\t"
                f"{attr(gene_id=tx['gene_id'], transcript_id=tx['transcript_id'], exon_number=str(exon_idx))}\n"
            )
    GTF_PATH.write_text("".join(lines))


def write_bam_and_gold() -> None:
    header_lines = ["@HD\tVN:1.6\tSO:coordinate\n"]
    for chrom, length in CONTIG_LENGTHS.items():
        header_lines.append(f"@SQ\tSN:{chrom}\tLN:{length}\n")

    sam_lines = list(header_lines)
    support = defaultdict(int)
    annotated = {
        (row["chrom"], row["intron_start"], row["intron_end"]): row
        for row in transcript_junction_rows()
    }
    for name, flag, chrom, pos, cigar in READ_SPECS:
        qlen = cigar_query_len(cigar)
        seq = ("ACGT" * ((qlen // 4) + 1))[:qlen]
        qual = "I" * qlen if flag & 4 == 0 else "*"
        rnext = "*"
        pnext = 0
        tlen = 0
        mapq = 60 if flag & 4 == 0 else 0
        seq_field = seq if flag & 4 == 0 else "*"
        sam_lines.append(
            f"{name}\t{flag}\t{chrom}\t{pos}\t{mapq}\t{cigar}\t{rnext}\t{pnext}\t{tlen}\t{seq_field}\t{qual}\n"
        )
        if flag & (4 | 256 | 2048):
            continue
        for intron_start, intron_end in junctions_from_cigar(pos, cigar):
            key = (chrom, intron_start, intron_end)
            if key in annotated:
                support[key] += 1

    sam_path = OUT_ROOT / "reads.sam"
    sam_path.write_text("".join(sam_lines))
    subprocess.check_call(["samtools", "sort", "-O", "bam", "-o", str(BAM_PATH), str(sam_path)])
    subprocess.check_call(["samtools", "index", str(BAM_PATH)])
    sam_path.unlink()

    rows = sorted(transcript_junction_rows(), key=lambda x: (x["transcript_id"], x["junction_index"]))
    with GOLD_PATH.open("w") as fh:
        fh.write("gene_id\ttranscript_id\tjunction_index\tchrom\tintron_start\tintron_end\tsupport_reads\n")
        for row in rows:
            key = (row["chrom"], row["intron_start"], row["intron_end"])
            fh.write(
                f"{row['gene_id']}\t{row['transcript_id']}\t{row['junction_index']}\t{row['chrom']}\t"
                f"{row['intron_start']}\t{row['intron_end']}\t{support.get(key, 0)}\n"
            )


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    write_gtf()
    write_bam_and_gold()
    print(f"wrote {GTF_PATH}, {BAM_PATH}, {BAM_PATH}.bai, {GOLD_PATH}")


if __name__ == "__main__":
    main()
