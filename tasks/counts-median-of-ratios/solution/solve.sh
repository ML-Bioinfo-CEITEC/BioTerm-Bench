#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
import numpy as np
import pandas as pd

counts = pd.read_csv("/app/data/counts.tsv", sep="\t", index_col=0)
arr = counts.to_numpy(dtype=float)
keep = np.all(arr > 0, axis=1)
kept = arr[keep]
log_c = np.log(kept)
logmean = log_c.mean(axis=1)
ratios = log_c - logmean[:, None]
sf_log = np.median(ratios, axis=0)
sf = np.exp(sf_log)

with open("/app/output/size_factors.tsv", "w") as fh:
    fh.write("sample\tsize_factor\n")
    for s, v in zip(counts.columns, sf):
        fh.write(f"{s}\t{v:.6f}\n")
PY
