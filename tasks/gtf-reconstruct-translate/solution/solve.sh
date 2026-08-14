#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
import csv
import re
from collections import defaultdict

ATTR_RE = re.compile(r'(\w+)\s+"([^"]+)"')
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


def revcomp(seq: str) -> str:
    table = str.maketrans("ACGTacgt", "TGCAtgca")
    return seq.translate(table)[::-1]


def load_fasta(path: str):
    seqs = {}
    name = None
    chunks = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    seqs[name] = "".join(chunks)
                name = line[1:].split()[0]
                chunks = []
            else:
                chunks.append(line.upper())
        if name is not None:
            seqs[name] = "".join(chunks)
    return seqs


genome = load_fasta("/app/data/genome.fa")
meta = {}
cds_spans = defaultdict(list)

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
            meta[tid] = {"gene_id": gid, "chrom": chrom, "strand": strand}
        elif feature == "CDS" and gid and tid:
            meta.setdefault(tid, {"gene_id": gid, "chrom": chrom, "strand": strand})
            cds_spans[tid].append((int(start), int(end)))

rows = []
for tid in sorted(cds_spans):
    tx = meta[tid]
    spans = sorted(cds_spans[tid], key=lambda x: x[0])
    seq_parts = [genome[tx["chrom"]][start - 1:end] for start, end in spans]
    if tx["strand"] == "-":
        cds = revcomp("".join(reversed(seq_parts)))
    else:
        cds = "".join(seq_parts)
    peptide = "".join(CODON_TABLE[cds[i:i + 3]] for i in range(0, len(cds), 3))
    rows.append([tid, tx["gene_id"], tx["strand"], str(len(cds)), str(len(peptide)), peptide])

with open("/app/output/proteins.tsv", "w", newline="") as fh:
    writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
    writer.writerow(["transcript_id", "gene_id", "strand", "cds_length", "peptide_length", "peptide"])
    writer.writerows(rows)
PY
