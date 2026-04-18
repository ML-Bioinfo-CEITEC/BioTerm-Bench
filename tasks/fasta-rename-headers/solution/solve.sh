#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
from pathlib import Path

mapping = {}
with open("/app/data/map.tsv") as fh:
    header = fh.readline()  # discard header row
    for line in fh:
        line = line.rstrip("\n")
        if not line:
            continue
        old, new = line.split("\t", 1)
        mapping[old] = new

out = Path("/app/output/renamed.fa").open("w")
with open("/app/data/in.fa") as fh:
    for line in fh:
        if line.startswith(">"):
            token = line[1:].split()[0] if line[1:].strip() else ""
            new_id = mapping.get(token, token)
            out.write(f">{new_id}\n")
        else:
            # Pass sequence lines through unchanged (preserves wrap width).
            out.write(line if line.endswith("\n") else line + "\n")
out.close()
PY
