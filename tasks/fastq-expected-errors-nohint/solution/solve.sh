#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
import math

rows = []
with open("/app/data/reads.fastq") as fh:
    while True:
        h = fh.readline()
        if not h:
            break
        seq = fh.readline().strip()
        fh.readline()
        qual = fh.readline().strip()
        q = [ord(c) - 33 for c in qual]
        errs = [10 ** (-x / 10) for x in q]
        ee = sum(errs)
        if ee <= 1.0:
            continue
        rows.append((h[1:].strip(), len(seq), sum(q) / len(q), ee,
                     -10 * math.log10(ee / len(q))))

rows.sort(key=lambda r: (-r[3], r[0]))
with open("/app/output/noisy_reads.tsv", "w") as fh:
    fh.write("read_id\tlength\tmean_q\texpected_errors\tequivalent_q\n")
    for rid, ln, mq, ee, eq in rows:
        fh.write(f"{rid}\t{ln}\t{mq:.4f}\t{ee:.4f}\t{eq:.4f}\n")
PY
