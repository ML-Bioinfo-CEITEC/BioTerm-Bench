#!/usr/bin/env python3
"""Generate stranded RNA-seq BAMs + GTF + featureCounts gold outputs.

Writes:
  /out/data/annot.gtf
  /out/data/sample_*.bam
  /out/data/sample_*.bam.bai
  /out/gold/gene_counts.tsv
  /out/gold/assignment_summary.tsv
"""
from __future__ import annotations

import csv
from pathlib import Path

import pysam

OUT_DATA = Path("/out/data")
OUT_GOLD = Path("/out/gold")

REF_NAME = "chrSyntheticRNA"
REF_LEN = 6000
READ_LEN = 75
SAMPLES = ["sample_A", "sample_B", "sample_C", "sample_D"]

GENES = [
    {
        "gene_id": "ENSGFC0001",
        "tx_id": "ENSTFC0001",
        "strand": "+",
        "exons": [(100, 189), (260, 349)],
        "counts": [14, 10, 19, 7],
    },
    {
        "gene_id": "ENSGFC0002",
        "tx_id": "ENSTFC0002",
        "strand": "-",
        "exons": [(100, 189), (260, 349)],
        "counts": [3, 16, 5, 14],
    },
    {
        "gene_id": "ENSGFC0003",
        "tx_id": "ENSTFC0003",
        "strand": "+",
        "exons": [(900, 989), (1060, 1149)],
        "counts": [18, 4, 11, 9],
    },
    {
        "gene_id": "ENSGFC0004",
        "tx_id": "ENSTFC0004",
        "strand": "-",
        "exons": [(900, 989), (1060, 1149)],
        "counts": [6, 13, 7, 17],
    },
    {
        "gene_id": "ENSGFC0005",
        "tx_id": "ENSTFC0005",
        "strand": "+",
        "exons": [(1700, 1794), (1850, 1944)],
        "counts": [9, 9, 15, 21],
    },
    {
        "gene_id": "ENSGFC0006",
        "tx_id": "ENSTFC0006",
        "strand": "-",
        "exons": [(2500, 2594), (2680, 2774)],
        "counts": [20, 8, 12, 5],
    },
]

INTERGENIC_READS = [7, 5, 6, 8]
UNMAPPED_READS = [3, 4, 2, 5]


def _write_gtf(path: Path) -> None:
    with path.open("w") as fh:
        for gene in GENES:
            start = min(s for s, _ in gene["exons"])
            end = max(e for _, e in gene["exons"])
            attrs = (
                f'gene_id "{gene["gene_id"]}"; '
                f'transcript_id "{gene["tx_id"]}"; '
                f'gene_name "{gene["gene_id"]}";'
            )
            fh.write(
                f"{REF_NAME}\tbioterm\tgene\t{start}\t{end}\t.\t{gene['strand']}\t.\t"
                f'gene_id "{gene["gene_id"]}"; gene_name "{gene["gene_id"]}";\n'
            )
            fh.write(
                f"{REF_NAME}\tbioterm\ttranscript\t{start}\t{end}\t.\t{gene['strand']}\t.\t"
                f"{attrs}\n"
            )
            for exon_no, (exon_start, exon_end) in enumerate(gene["exons"], start=1):
                fh.write(
                    f"{REF_NAME}\tbioterm\texon\t{exon_start}\t{exon_end}\t.\t{gene['strand']}\t.\t"
                    f'{attrs} exon_number "{exon_no}";\n'
                )


def _make_aln(
    qname: str,
    flag: int,
    start_1based: int,
    mapq: int = 60,
) -> pysam.AlignedSegment:
    aln = pysam.AlignedSegment()
    aln.query_name = qname
    aln.flag = flag
    aln.reference_id = 0
    aln.reference_start = start_1based - 1
    aln.mapping_quality = mapq
    aln.cigarstring = f"{READ_LEN}M"
    aln.query_sequence = ("ACGT" * ((READ_LEN // 4) + 1))[:READ_LEN]
    aln.query_qualities = pysam.qualitystring_to_array("I" * READ_LEN)
    return aln


def _write_bam(sample_idx: int, sample_name: str, out_path: Path) -> None:
    header = {
        "HD": {"VN": "1.6", "SO": "unsorted"},
        "SQ": [{"SN": REF_NAME, "LN": REF_LEN}],
    }
    raw_bam = out_path.with_suffix(".unsorted.bam")
    with pysam.AlignmentFile(raw_bam, "wb", header=header) as bam:
        read_no = 0
        for gene in GENES:
            flag = 16 if gene["strand"] == "+" else 0
            exon_positions = [start for start, _ in gene["exons"]]
            for i in range(gene["counts"][sample_idx]):
                exon_start = exon_positions[i % len(exon_positions)]
                offset = (i * 7 + sample_idx * 3) % 8
                bam.write(
                    _make_aln(
                        qname=f"{sample_name}_{gene['gene_id']}_{i:03d}",
                        flag=flag,
                        start_1based=exon_start + offset,
                    )
                )
                read_no += 1

        for i in range(INTERGENIC_READS[sample_idx]):
            bam.write(
                _make_aln(
                    qname=f"{sample_name}_intergenic_{i:03d}",
                    flag=0,
                    start_1based=3200 + i * 11,
                )
            )
            read_no += 1

        for i in range(UNMAPPED_READS[sample_idx]):
            aln = pysam.AlignedSegment()
            aln.query_name = f"{sample_name}_unmapped_{i:03d}"
            aln.flag = 4
            aln.query_sequence = ("TGCA" * ((READ_LEN // 4) + 1))[:READ_LEN]
            aln.query_qualities = pysam.qualitystring_to_array("I" * READ_LEN)
            bam.write(aln)
            read_no += 1

    pysam.sort("-o", str(out_path), str(raw_bam))
    pysam.index(str(out_path))
    raw_bam.unlink()
    print(f"wrote {out_path} ({read_no} reads)")


def _write_gold(gtf: Path, bam_paths: list[Path]) -> None:
    raw_counts = OUT_GOLD / "_featurecounts.tsv"
    import subprocess

    subprocess.run(
        [
            "featureCounts",
            "-T",
            "1",
            "-a",
            str(gtf),
            "-o",
            str(raw_counts),
            "-t",
            "exon",
            "-g",
            "gene_id",
            "-s",
            "2",
            *map(str, bam_paths),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    with raw_counts.open() as fh, (OUT_GOLD / "gene_counts.tsv").open("w") as out_fh:
        reader = csv.reader((line for line in fh if not line.startswith("#")), delimiter="\t")
        header = next(reader)
        sample_cols = [Path(x).stem for x in header[6:]]
        out_fh.write("gene_id\t" + "\t".join(sample_cols) + "\n")
        for row in reader:
            out_fh.write(row[0] + "\t" + "\t".join(row[6:]) + "\n")

    wanted = ["Assigned", "Unassigned_NoFeatures", "Unassigned_Unmapped"]
    summary_path = raw_counts.with_suffix(raw_counts.suffix + ".summary")
    summary_rows: dict[str, list[str]] = {}
    with summary_path.open() as fh:
        reader = csv.reader(fh, delimiter="\t")
        header = next(reader)
        sample_cols = [Path(x).stem for x in header[1:]]
        for row in reader:
            if row and row[0] in wanted:
                summary_rows[row[0]] = row[1:]

    with (OUT_GOLD / "assignment_summary.tsv").open("w") as out_fh:
        out_fh.write("status\t" + "\t".join(sample_cols) + "\n")
        for key in wanted:
            out_fh.write(key + "\t" + "\t".join(summary_rows[key]) + "\n")

    raw_counts.unlink()
    summary_path.unlink()


def main() -> None:
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    OUT_GOLD.mkdir(parents=True, exist_ok=True)

    gtf = OUT_DATA / "annot.gtf"
    _write_gtf(gtf)

    bam_paths = []
    for sample_idx, sample_name in enumerate(SAMPLES):
        bam_path = OUT_DATA / f"{sample_name}.bam"
        _write_bam(sample_idx, sample_name, bam_path)
        bam_paths.append(bam_path)

    _write_gold(gtf, bam_paths)
    print("wrote featureCounts gold outputs")


if __name__ == "__main__":
    main()
