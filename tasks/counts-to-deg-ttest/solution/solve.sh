#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 - <<'PY'
import numpy as np
import pandas as pd
from scipy import stats

counts = pd.read_csv("/app/data/counts.tsv", sep="\t", index_col=0)
samples = pd.read_csv("/app/data/samples.tsv", sep="\t")

groups = dict(zip(samples["sample"], samples["group"]))
ctrl = [s for s in counts.columns if groups[s] == "ctrl"]
trt = [s for s in counts.columns if groups[s] == "trt"]

lib = counts.sum(axis=0)
cpm = counts.div(lib, axis=1) * 1_000_000

rows = []
for gid in counts.index:
    a = cpm.loc[gid, ctrl].to_numpy(dtype=float)
    b = cpm.loc[gid, trt].to_numpy(dtype=float)
    res = stats.ttest_ind(a, b, equal_var=False)
    t = float(res.statistic)
    p = float(res.pvalue)
    if np.isnan(t):
        t = 0.0
    if np.isnan(p):
        p = 1.0
    rows.append((gid, t, p, float(a.mean()), float(b.mean())))

rows.sort(key=lambda r: (-abs(r[1]), r[0]))
top = rows[:20]

with open("/app/output/top_deg.tsv", "w") as fh:
    fh.write("gene_id\tt_stat\tp_value\tmean_cpm_ctrl\tmean_cpm_trt\n")
    for gid, t, p, mc, mt in top:
        fh.write(f"{gid}\t{t:.4f}\t{p:.6e}\t{mc:.4f}\t{mt:.4f}\n")
PY
