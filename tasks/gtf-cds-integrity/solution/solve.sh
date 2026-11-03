#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
import re
from collections import defaultdict

COMP = str.maketrans("ACGT", "TGCA")
STOP = {"TAA", "TAG", "TGA"}


def rc(s):
    return s.translate(COMP)[::-1]


genome, name, buf = {}, None, []
for line in open("/app/data/genome.fa"):
    if line.startswith(">"):
        if name:
            genome[name] = "".join(buf)
        name, buf = line[1:].strip().split()[0], []
    else:
        buf.append(line.strip())
if name:
    genome[name] = "".join(buf)

cds = defaultdict(list)
info = {}
for line in open("/app/data/annotation.gtf"):
    if line.startswith("#"):
        continue
    f = line.rstrip("\n").split("\t")
    if f[2] != "CDS":
        continue
    m = re.search(r'transcript_id "([^"]+)"', f[8])
    tx = m.group(1)
    cds[tx].append((int(f[3]), int(f[4])))
    info[tx] = (f[0], f[6])

rows = []
for tx, blocks in cds.items():
    chrom, strand = info[tx]
    ordered = sorted(blocks) if strand == "+" else sorted(blocks, reverse=True)
    parts = []
    for s, e in ordered:
        piece = genome[chrom][s - 1:e]
        parts.append(piece if strand == "+" else rc(piece))
    seq = "".join(parts)
    n = len(seq)
    codons = [seq[i:i + 3] for i in range(0, n - n % 3, 3)]
    has_start = bool(codons) and codons[0] == "ATG"
    has_stop = bool(codons) and codons[-1] in STOP
    internal = sum(1 for c in codons[:-1] if c in STOP)
    if n % 3:
        status = "not_multiple_of_three"
    elif not has_start:
        status = "no_start_codon"
    elif internal:
        status = "internal_stop"
    elif not has_stop:
        status = "no_stop_codon"
    else:
        status = "ok"
    rows.append((tx, chrom, strand, n, "yes" if has_start else "no",
                 "yes" if has_stop else "no", internal, status))

rows.sort(key=lambda r: r[0])
with open("/app/output/cds_report.tsv", "w") as fh:
    fh.write("tx_id\tchrom\tstrand\tcds_len\thas_start\thas_stop\t"
             "n_internal_stops\tstatus\n")
    for r in rows:
        fh.write("\t".join(map(str, r)) + "\n")
PY
