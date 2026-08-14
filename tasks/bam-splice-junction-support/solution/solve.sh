#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
import csv
import re
from collections import defaultdict

import pysam

ATTR_RE = re.compile(r'(\w+)\s+"([^"]+)"')


def parse_gtf():
    transcripts = {}
    exons = defaultdict(list)
    with open("/app/data/annot.gtf") as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 9:
                continue
            chrom, _, feature, start, end, _, strand, _, attrs_raw = fields
            attrs = dict(ATTR_RE.findall(attrs_raw))
            gid = attrs.get("gene_id")
            tid = attrs.get("transcript_id")
            if feature == "transcript" and gid and tid:
                transcripts[tid] = {"gene_id": gid, "chrom": chrom, "strand": strand}
            elif feature == "exon" and gid and tid:
                exons[tid].append((int(start), int(end)))
    rows = []
    for tid, meta in transcripts.items():
        ordered = sorted(exons[tid], key=lambda x: x[0])
        if meta["strand"] == "-":
            ordered = list(reversed(ordered))
        for idx, (left, right) in enumerate(zip(ordered, ordered[1:]), start=1):
            rows.append(
                {
                    "gene_id": meta["gene_id"],
                    "transcript_id": tid,
                    "junction_index": idx,
                    "chrom": meta["chrom"],
                    "intron_start": left[1] + 1,
                    "intron_end": right[0] - 1,
                }
            )
    return sorted(rows, key=lambda x: (x["transcript_id"], x["junction_index"]))


def observed_support():
    counts = defaultdict(int)
    with pysam.AlignmentFile("/app/data/reads.bam", "rb") as bam:
        for rec in bam.fetch(until_eof=True):
            if rec.is_unmapped or rec.is_secondary or rec.is_supplementary:
                continue
            ref_pos = rec.reference_start + 1
            for op, length in rec.cigartuples or []:
                if op == 3:  # N
                    counts[(rec.reference_name, ref_pos, ref_pos + length - 1)] += 1
                    ref_pos += length
                elif op in {0, 2, 7, 8}:  # M,D,=,X
                    ref_pos += length
    return counts


junctions = parse_gtf()
support = observed_support()

with open("/app/output/support.tsv", "w", newline="") as fh:
    writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
    writer.writerow(
        ["gene_id", "transcript_id", "junction_index", "chrom", "intron_start", "intron_end", "support_reads"]
    )
    for row in junctions:
        writer.writerow(
            [
                row["gene_id"],
                row["transcript_id"],
                row["junction_index"],
                row["chrom"],
                row["intron_start"],
                row["intron_end"],
                support.get((row["chrom"], row["intron_start"], row["intron_end"]), 0),
            ]
        )
PY
