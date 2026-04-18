#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

snpEff -noStats \
    -c /app/data/snpeff.config \
    -dataDir /app/data/snpeff_db/data \
    SARSCoV2 \
    /app/data/variants.vcf > /tmp/annotated.vcf

python3 - <<'PY' > /app/output/impact_counts.json
import json

impacts = {"HIGH": 0, "MODERATE": 0, "LOW": 0, "MODIFIER": 0}
total = 0
with open("/tmp/annotated.vcf") as fh:
    for line in fh:
        if line.startswith("#") or not line.strip():
            continue
        cols = line.rstrip("\n").split("\t")
        if len(cols) < 8:
            continue
        total += 1
        info = cols[7]
        ann_field = None
        for kv in info.split(";"):
            if kv.startswith("ANN="):
                ann_field = kv[4:]
                break
        if ann_field is None:
            continue
        first_ann = ann_field.split(",")[0]
        subfields = first_ann.split("|")
        impact = subfields[2]
        if impact in impacts:
            impacts[impact] += 1

out = {**impacts, "total": total}
print(json.dumps(out, sort_keys=True, indent=2))
PY
