#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
import pandas as pd

counts = pd.read_csv("/app/data/counts.tsv", sep="\t")
lengths = pd.read_csv("/app/data/gene_lengths.tsv", sep="\t")

lengths = lengths.set_index("gene_id")["length_bp"]
samples = [c for c in counts.columns if c != "gene_id"]

rpk = counts.copy()
for s in samples:
    rpk[s] = counts[s] / (lengths.loc[counts["gene_id"]].values / 1000.0)

tpm = rpk.copy()
for s in samples:
    scale = rpk[s].sum() / 1_000_000
    tpm[s] = rpk[s] / scale

tpm.to_csv("/app/output/tpm.tsv", sep="\t", index=False,
           float_format="%.6f")
PY
