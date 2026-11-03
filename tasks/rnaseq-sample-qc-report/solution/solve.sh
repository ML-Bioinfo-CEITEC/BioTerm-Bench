#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
import statistics

rows = [ln.rstrip("\n").split("\t") for ln in open("/app/data/counts.tsv")]
samples = rows[0][1:]
genes = [r[0] for r in rows[1:]]
counts = {s: {r[0]: int(r[i + 1]) for r in rows[1:]} for i, s in enumerate(samples)}

lib = {s: sum(counts[s].values()) for s in samples}
detected = {s: sum(1 for g in genes if counts[s][g] > 0) for s in samples}
median_lib = statistics.median(lib.values())
failing = {s for s in samples if lib[s] < 0.3 * median_lib or detected[s] < 1200}

with open("/app/output/sample_qc.tsv", "w") as fh:
    fh.write("sample\tlibrary_size\tn_detected\tstatus\n")
    for s in samples:
        fh.write(f"{s}\t{lib[s]}\t{detected[s]}\t{'fail' if s in failing else 'pass'}\n")

keep = [s for s in samples if s not in failing]
cpm = {s: {g: counts[s][g] * 1e6 / lib[s] for g in genes} for s in keep}
kept = [g for g in genes if sum(1 for s in keep if cpm[s][g] >= 1.0) >= 3]

with open("/app/output/gene_filter.tsv", "w") as fh:
    fh.write("gene\tn_samples_expressed\tmean_cpm\n")
    for g in kept:
        n_exp = sum(1 for s in keep if cpm[s][g] >= 1.0)
        fh.write(f"{g}\t{n_exp}\t{sum(cpm[s][g] for s in keep) / len(keep):.4f}\n")

with open("/app/output/summary.tsv", "w") as fh:
    fh.write("metric\tvalue\n")
    fh.write(f"n_samples_total\t{len(samples)}\n")
    fh.write(f"n_samples_passing\t{len(keep)}\n")
    fh.write(f"n_genes_total\t{len(genes)}\n")
    fh.write(f"n_genes_retained\t{len(kept)}\n")
    fh.write(f"median_library_size\t{median_lib:.1f}\n")
PY
