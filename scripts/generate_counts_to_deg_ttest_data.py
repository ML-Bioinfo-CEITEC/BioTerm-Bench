#!/usr/bin/env python3
"""Generate a counts matrix + gold top-N DEG table by Welch t-test.

Writes:
  /out/data/counts.tsv
  /out/data/samples.tsv
  /out/gold/top_deg.tsv
"""
from __future__ import annotations

import random
from pathlib import Path

import numpy as np
from scipy import stats

SEED = 20260418
N_GENES = 300
TOP_N = 20

DATA = Path("/out/data/counts.tsv")
SAMPLES = Path("/out/data/samples.tsv")
GOLD = Path("/out/gold/top_deg.tsv")

GROUPS = [("ctrl_1", "ctrl"), ("ctrl_2", "ctrl"), ("ctrl_3", "ctrl"),
          ("trt_1", "trt"), ("trt_2", "trt"), ("trt_3", "trt")]


def main() -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(SEED)

    sample_ids = [s for s, _ in GROUPS]
    groups = [g for _, g in GROUPS]
    lib_sizes = rng.integers(8_000_000, 12_000_000, size=6)

    gene_ids = [f"GENE{g:04d}" for g in range(1, N_GENES + 1)]

    counts = np.zeros((N_GENES, 6), dtype=np.int64)
    for gi, gid in enumerate(gene_ids):
        base = rng.lognormal(mean=4.5, sigma=1.5)
        base = max(5.0, min(base, 5000.0))
        fc = 1.0
        if gi < 30:
            fc = rng.uniform(2.5, 5.0)
        elif gi < 45:
            fc = 1.0 / rng.uniform(2.5, 5.0)
        for si in range(6):
            mu = base * (fc if groups[si] == "trt" else 1.0)
            mu *= lib_sizes[si] / 1e7
            counts[gi, si] = max(0, int(rng.poisson(mu)))

    with DATA.open("w") as fh:
        fh.write("gene_id\t" + "\t".join(sample_ids) + "\n")
        for gi, gid in enumerate(gene_ids):
            fh.write(gid + "\t" + "\t".join(str(c) for c in counts[gi]) + "\n")

    with SAMPLES.open("w") as fh:
        fh.write("sample\tgroup\n")
        for s, g in GROUPS:
            fh.write(f"{s}\t{g}\n")

    # CPM normalization (per-sample)
    lib = counts.sum(axis=0)
    cpm = counts / lib * 1_000_000

    ctrl_idx = [i for i, g in enumerate(groups) if g == "ctrl"]
    trt_idx = [i for i, g in enumerate(groups) if g == "trt"]

    rows = []
    for gi, gid in enumerate(gene_ids):
        a = cpm[gi, ctrl_idx]
        b = cpm[gi, trt_idx]
        res = stats.ttest_ind(a, b, equal_var=False)
        t = float(res.statistic)
        p = float(res.pvalue)
        m_ctrl = float(a.mean())
        m_trt = float(b.mean())
        if np.isnan(t):
            t = 0.0
        if np.isnan(p):
            p = 1.0
        rows.append((gid, t, p, m_ctrl, m_trt))

    rows.sort(key=lambda r: (-abs(r[1]), r[0]))
    top = rows[:TOP_N]

    with GOLD.open("w") as fh:
        fh.write("gene_id\tt_stat\tp_value\tmean_cpm_ctrl\tmean_cpm_trt\n")
        for gid, t, p, mc, mt in top:
            fh.write(
                f"{gid}\t{t:.4f}\t{p:.6e}\t{mc:.4f}\t{mt:.4f}\n"
            )
    print(f"wrote {DATA}, {SAMPLES}, {GOLD}")


if __name__ == "__main__":
    main()
