#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
import gzip
import json


ADAPTER = "AGATCGGAAGAGC"


def normalize_id(header: str) -> str:
    token = header.split()[0]
    if token.endswith("/1") or token.endswith("/2"):
        token = token[:-2]
    return token


def load_fastq(path):
    records = {}
    total = 0
    with gzip.open(path, "rt") as fh:
        while True:
            header = fh.readline().rstrip()
            if not header:
                break
            seq = fh.readline().rstrip()
            fh.readline()
            qual = fh.readline().rstrip()
            total += 1
            records[normalize_id(header[1:])] = (seq, [ord(ch) - 33 for ch in qual])
    return total, records


total_r1, r1 = load_fastq("/app/data/reads_R1.fastq.gz")
total_r2, r2 = load_fastq("/app/data/reads_R2.fastq.gz")
ids1 = set(r1)
ids2 = set(r2)
proper = sorted(ids1 & ids2)
orph_r1 = sorted(ids1 - ids2)
orph_r2 = sorted(ids2 - ids1)

adapter_pairs = 0
adapter_both = 0
q30_num_r1 = q30_den_r1 = 0
q30_num_r2 = q30_den_r2 = 0
for rid in proper:
    seq1, qual1 = r1[rid]
    seq2, qual2 = r2[rid]
    has1 = ADAPTER in seq1
    has2 = ADAPTER in seq2
    if has1 or has2:
        adapter_pairs += 1
    if has1 and has2:
        adapter_both += 1
    q30_num_r1 += sum(1 for q in qual1 if q >= 30)
    q30_den_r1 += len(qual1)
    q30_num_r2 += sum(1 for q in qual2 if q >= 30)
    q30_den_r2 += len(qual2)

summary = {
    "adapter_pairs": adapter_pairs,
    "adapter_pairs_both_mates": adapter_both,
    "orphan_r1": len(orph_r1),
    "orphan_r2": len(orph_r2),
    "proper_pairs": len(proper),
    "q30_frac_r1": round(q30_num_r1 / q30_den_r1, 4) if q30_den_r1 else 0.0,
    "q30_frac_r2": round(q30_num_r2 / q30_den_r2, 4) if q30_den_r2 else 0.0,
    "total_r1": total_r1,
    "total_r2": total_r2,
}
with open("/app/output/summary.json", "w") as fh:
    json.dump(summary, fh, indent=2, sort_keys=True)
    fh.write("\n")

with open("/app/output/orphans.tsv", "w") as fh:
    fh.write("read_id\tpresent_in\n")
    for rid in orph_r1:
        fh.write(f"{rid}\tR1\n")
    for rid in orph_r2:
        fh.write(f"{rid}\tR2\n")
PY
