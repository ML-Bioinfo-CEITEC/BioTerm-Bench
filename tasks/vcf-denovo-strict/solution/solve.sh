#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
import gzip

order = {"chr1": 0, "chr2": 1}
rows = []
with gzip.open("/app/data/trio.vcf.gz", "rt") as fh:
    for line in fh:
        if line.startswith("#"):
            continue
        f = line.rstrip("\n").split("\t")
        chrom, pos, ref, alt, filt = f[0], int(f[1]), f[3], f[4], f[6]
        if chrom not in order:
            continue
        if filt not in ("PASS", "."):
            continue
        if len(ref) != 1 or "," in alt or len(alt) != 1:
            continue
        keys = f[8].split(":")
        child, father, mother = (dict(zip(keys, s.split(":"))) for s in f[9:12])
        if child.get("GT") not in ("0/1", "1/0"):
            continue
        if father.get("GT") != "0/0" or mother.get("GT") != "0/0":
            continue
        try:
            c_ref, c_alt = (int(x) for x in child["AD"].split(","))
            dpc, dpf, dpm = int(child["DP"]), int(father["DP"]), int(mother["DP"])
            f_alt = int(father["AD"].split(",")[1])
            m_alt = int(mother["AD"].split(",")[1])
        except (ValueError, KeyError):
            continue
        ab = c_alt / (c_ref + c_alt) if (c_ref + c_alt) else 0.0
        ok = (dpc >= 10 and dpf >= 10 and dpm >= 10
              and 0.25 <= ab <= 0.75 and f_alt == 0 and m_alt == 0)
        rows.append((chrom, pos, ref, alt, "denovo" if ok else "uncertain", f"{ab:.4f}"))

rows.sort(key=lambda r: (order[r[0]], r[1]))
with open("/app/output/denovo.tsv", "w") as fh:
    fh.write("chrom\tpos\tref\talt\tclass\tchild_ab\n")
    for r in rows:
        fh.write("\t".join(map(str, r)) + "\n")
PY
