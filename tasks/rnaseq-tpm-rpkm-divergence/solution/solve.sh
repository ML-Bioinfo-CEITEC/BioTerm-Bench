#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
rows = [ln.rstrip("\n").split("\t") for ln in open("/app/data/counts.tsv")]
samples = rows[0][2:]
genes = [r[0] for r in rows[1:]]
length = {r[0]: int(r[1]) for r in rows[1:]}
counts = {s: {r[0]: int(r[i + 2]) for r in rows[1:]} for i, s in enumerate(samples)}

tpm, rpkm = {}, {}
for s in samples:
    rates = {g: counts[s][g] / (length[g] / 1000) for g in genes}
    denom = sum(rates.values())
    tpm[s] = {g: rates[g] / denom * 1e6 for g in genes}
    total = sum(counts[s].values())
    rpkm[s] = {g: counts[s][g] / (length[g] / 1000) / (total / 1e6) for g in genes}

mean_tpm = {g: sum(tpm[s][g] for s in samples) / len(samples) for g in genes}
mean_rpkm = {g: sum(rpkm[s][g] for s in samples) / len(samples) for g in genes}


def ranks(vals):
    order = sorted(genes, key=lambda g: (-vals[g], g))
    return {g: i + 1 for i, g in enumerate(order)}


rt, rr = ranks(mean_tpm), ranks(mean_rpkm)
top = sorted(genes, key=lambda g: (-abs(rt[g] - rr[g]), g))[:40]

with open("/app/output/rank_divergence.tsv", "w") as fh:
    fh.write("gene\tmean_tpm\tmean_rpkm\trank_tpm\trank_rpkm\trank_shift\n")
    for g in top:
        fh.write(f"{g}\t{mean_tpm[g]:.4f}\t{mean_rpkm[g]:.4f}\t{rt[g]}\t{rr[g]}\t"
                 f"{abs(rt[g] - rr[g])}\n")
PY
