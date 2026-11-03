#!/usr/bin/env python3
"""Generate v1.0 hard candidates, batch 5 -- scale and multi-deliverable work.

Batches 1-4 left two of the eight hardness axes unused, and the screen showed
why that matters: the strongest e-INFRA model solved 8 of the 9 algorithmic
tasks on every attempt. Knowing an algorithm is not the binding constraint.

These three attack what is left:

* `kmer-index-similar-pairs` cannot be brute-forced. Two hundred million
  sequence pairs is out of reach in the agent's time budget, so the task is
  passed only by inverting the problem into a k-mer index.
* `depth-gc-bias-correction` is a chain: bin, summarise, derive factors, apply,
  then threshold. An error in any link survives to the output.
* `rnaseq-sample-qc-report` has three deliverables and all three are graded, so
  a run that gets two right still scores zero.

    docker run --rm -v "$PWD":/repo -w /repo bioterm-base:v1 \
        python3 scripts/generate_hard_candidates_batch5.py
"""

from __future__ import annotations

import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hard_candidate_common import write_multi_task, write_task  # noqa: E402


# ------------------------------------------------------- 17. k-mer index scale
def gen_kmer_index(root: Path) -> None:
    name = "kmer-index-similar-pairs"
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(555111)
    K, THRESH, N = 15, 60, 20000

    seqs: dict[str, str] = {}
    for i in range(1, N + 1):
        seqs[f"seq{i:05d}"] = "".join(rng.choice("ACGT") for _ in range(150))

    # Plant related pairs across a range of divergence, so some clear the
    # threshold and some deliberately fall just short.
    names = list(seqs)
    for _ in range(70):
        a = rng.choice(names)
        b = rng.choice(names)
        while b == a:
            b = rng.choice(names)
        src = seqs[a]
        n_mut = rng.randrange(1, 12)
        pos = rng.sample(range(150), n_mut)
        out = list(src)
        for p in pos:
            out[p] = rng.choice([x for x in "ACGT" if x != out[p]])
        seqs[b] = "".join(out)

    with (d / "sequences.fasta").open("w") as fh:
        for n in names:
            fh.write(f">{n}\n{seqs[n]}\n")

    index: dict[str, list[str]] = defaultdict(list)
    for n in names:
        for km in {seqs[n][i:i + K] for i in range(150 - K + 1)}:
            index[km].append(n)
    shared: dict[tuple[str, str], int] = defaultdict(int)
    for holders in index.values():
        if len(holders) < 2:
            continue
        holders = sorted(holders)
        for i, x in enumerate(holders):
            for y in holders[i + 1:]:
                shared[(x, y)] += 1

    rows = sorted(((a, b, c) for (a, b), c in shared.items() if c >= THRESH),
                  key=lambda r: (-r[2], r[0], r[1]))
    lines = ["seq_a\tseq_b\tn_shared_kmers"]
    lines += [f"{a}\t{b}\t{c}" for a, b, c in rows]
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/sequences.fasta` holds 20000 sequences of 150 bases each.

    Report every pair of sequences that shares at least **60 distinct 15-mers**.

    A sequence's k-mer set is the set of distinct 15-base substrings at every
    offset; count a k-mer once per sequence however often it occurs. The shared
    count for a pair is the size of the intersection of their two sets. Use the
    forward strand only.

    Comparing all pairs directly means two hundred million comparisons and will
    not finish in the time available. Build an index from each 15-mer to the
    sequences containing it, then count shared k-mers only for pairs that
    actually co-occur in some bucket. Almost every bucket holds one sequence,
    so the work collapses.

    Write `/app/output/similar_pairs.tsv` with header

    `seq_a\tseq_b\tn_shared_kmers`

    one row per qualifying pair, with `seq_a` the lexicographically smaller
    name. Sort by descending `n_shared_kmers`, then by `seq_a`, then by
    `seq_b`. If no pair qualifies, write the header alone.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
from collections import defaultdict

K, THRESH = 15, 60
seqs, name, buf = {}, None, []
for line in open("/app/data/sequences.fasta"):
    if line.startswith(">"):
        if name:
            seqs[name] = "".join(buf)
        name, buf = line[1:].strip(), []
    else:
        buf.append(line.strip())
if name:
    seqs[name] = "".join(buf)

index = defaultdict(list)
for n, s in seqs.items():
    for km in {s[i:i + K] for i in range(len(s) - K + 1)}:
        index[km].append(n)

shared = defaultdict(int)
for holders in index.values():
    if len(holders) < 2:
        continue
    holders = sorted(holders)
    for i, x in enumerate(holders):
        for y in holders[i + 1:]:
            shared[(x, y)] += 1

rows = sorted((( a, b, c) for (a, b), c in shared.items() if c >= THRESH),
              key=lambda r: (-r[2], r[0], r[1]))
with open("/app/output/similar_pairs.tsv", "w") as fh:
    fh.write("seq_a\tseq_b\tn_shared_kmers\n")
    for a, b, c in rows:
        fh.write(f"{a}\t{b}\t{c}\n")
PY
"""
    write_task(name, "search", ["kmer", "indexing", "scale", "similarity"],
               instruction, expected, solve, "/app/output/similar_pairs.tsv")
    near = sum(1 for (a, b), c in shared.items() if 40 <= c < 60)
    print(f"  {name}: {len(rows)} pairs at/above {THRESH}, {near} near-misses")


# ------------------------------------------------------- 18. GC bias chain
def gen_gc_bias(root: Path) -> None:
    name = "depth-gc-bias-correction"
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(246810)

    windows = []
    for c in range(1, 4):
        chrom = f"chr{c}"
        for w in range(700):
            gc = min(0.75, max(0.25, rng.gauss(0.45, 0.09)))
            # Depth is biased by GC, which is what the correction must remove.
            bias = 1.0 - 3.2 * (gc - 0.45) ** 2 * 4
            depth = max(0.0, rng.gauss(40.0 * bias, 3.0))
            if rng.random() < 0.02:                   # planted true outliers
                depth *= rng.choice([0.35, 2.4])
            windows.append((chrom, w * 1000, (w + 1) * 1000, round(gc, 4), round(depth, 2)))

    with (d / "windows.tsv").open("w") as fh:
        fh.write("chrom\tstart\tend\tgc\tdepth\n")
        for row in windows:
            fh.write("\t".join(map(str, row)) + "\n")

    def gc_bin(gc: float) -> int:
        return min(19, int(gc * 20))

    by_bin = defaultdict(list)
    for _c, _s, _e, gc, depth in windows:
        by_bin[gc_bin(gc)].append(depth)
    global_median = statistics.median([w[4] for w in windows])
    factors = {}
    for b, vals in by_bin.items():
        med = statistics.median(vals)
        factors[b] = 1.0 if len(vals) < 50 or med == 0 else global_median / med

    corrected = []
    for chrom, s, e, gc, depth in windows:
        corrected.append((chrom, s, e, gc, depth, depth * factors[gc_bin(gc)]))
    cvals = sorted(x[5] for x in corrected)
    cmed = statistics.median(cvals)
    lo, hi = 0.5 * cmed, 1.5 * cmed

    order = {"chr1": 0, "chr2": 1, "chr3": 2}
    flagged = sorted((x for x in corrected if x[5] < lo or x[5] > hi),
                     key=lambda x: (order[x[0]], x[1]))
    lines = ["chrom\tstart\tend\tgc\traw_depth\tcorrected_depth\tflag"]
    for chrom, s, e, gc, depth, cd in flagged:
        lines.append(f"{chrom}\t{s}\t{e}\t{gc:.4f}\t{depth:.2f}\t{cd:.4f}\t"
                     f"{'low' if cd < lo else 'high'}")
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/windows.tsv` gives 2100 genomic windows with their GC fraction
    and raw sequencing depth. Depth in this dataset is biased by GC content.

    Correct the bias, then flag the windows that are still unusual.

    Assign every window to one of twenty GC bins by
    `bin = min(19, int(gc * 20))`. Take the median raw depth of all windows,
    and the median raw depth within each bin. A bin's correction factor is
    `overall_median / bin_median`, except that a bin holding fewer than 50
    windows, or whose median is zero, gets a factor of exactly `1.0`.

    A window's corrected depth is its raw depth times its bin's factor.

    Now take the median of all 2100 corrected depths and flag every window
    whose corrected depth is below half that median (`low`) or above one and a
    half times it (`high`).

    Write `/app/output/flagged_windows.tsv` with header

    `chrom\tstart\tend\tgc\traw_depth\tcorrected_depth\tflag`

    one row per flagged window, sorted by chromosome (`chr1`, `chr2`, `chr3`)
    then start, echoing `gc` to four decimals and `raw_depth` to two, with
    `corrected_depth` to four decimals.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
import statistics
from collections import defaultdict

rows = []
with open("/app/data/windows.tsv") as fh:
    next(fh)
    for line in fh:
        c, s, e, gc, dp = line.rstrip("\n").split("\t")
        rows.append((c, int(s), int(e), float(gc), float(dp)))


def gc_bin(gc):
    return min(19, int(gc * 20))


by_bin = defaultdict(list)
for r in rows:
    by_bin[gc_bin(r[3])].append(r[4])

overall = statistics.median([r[4] for r in rows])
factors = {}
for b, vals in by_bin.items():
    med = statistics.median(vals)
    factors[b] = 1.0 if len(vals) < 50 or med == 0 else overall / med

corrected = [(r[0], r[1], r[2], r[3], r[4], r[4] * factors[gc_bin(r[3])]) for r in rows]
cmed = statistics.median([x[5] for x in corrected])
lo, hi = 0.5 * cmed, 1.5 * cmed

order = {"chr1": 0, "chr2": 1, "chr3": 2}
flagged = sorted((x for x in corrected if x[5] < lo or x[5] > hi),
                 key=lambda x: (order[x[0]], x[1]))

with open("/app/output/flagged_windows.tsv", "w") as fh:
    fh.write("chrom\tstart\tend\tgc\traw_depth\tcorrected_depth\tflag\n")
    for c, s, e, gc, dp, cd in flagged:
        fh.write(f"{c}\t{s}\t{e}\t{gc:.4f}\t{dp:.2f}\t{cd:.4f}\t"
                 f"{'low' if cd < lo else 'high'}\n")
PY
"""
    write_task(name, "qc", ["coverage", "gc-bias", "normalisation", "outliers"],
               instruction, expected, solve, "/app/output/flagged_windows.tsv", tol=1e-3)
    print(f"  {name}: {len(flagged)} flagged of {len(windows)} windows")


# --------------------------------------------- 19. three graded deliverables
def gen_multi_qc(root: Path) -> None:
    name = "rnaseq-sample-qc-report"
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(30303)

    genes = [f"ENSG{i:05d}" for i in range(1, 4001)]
    samples = [f"S{i:02d}" for i in range(1, 13)]
    bad = {"S04", "S09"}
    # Real expression is bimodal: most genes are off in any given tissue. A
    # unimodal draw would leave every gene above the CPM threshold and the
    # gene-filter deliverable would grade nothing.
    expressed = {g: rng.random() < 0.55 for g in genes}
    counts: dict[str, dict[str, int]] = {}
    for s in samples:
        depth = rng.randrange(300_000, 900_000) if s not in bad else rng.randrange(20_000, 60_000)
        col = {}
        for g in genes:
            base = (rng.lognormvariate(2.0, 1.6) if expressed[g]
                    else rng.lognormvariate(-2.2, 1.4))
            col[g] = int(base * depth / 400_000)
        counts[s] = col

    with (d / "counts.tsv").open("w") as fh:
        fh.write("gene\t" + "\t".join(samples) + "\n")
        for g in genes:
            fh.write(g + "\t" + "\t".join(str(counts[s][g]) for s in samples) + "\n")

    lib = {s: sum(counts[s].values()) for s in samples}
    detected = {s: sum(1 for g in genes if counts[s][g] > 0) for s in samples}
    median_lib = statistics.median(lib.values())
    failing = {s for s in samples if lib[s] < 0.3 * median_lib or detected[s] < 1200}

    sample_lines = ["sample\tlibrary_size\tn_detected\tstatus"]
    for s in samples:
        sample_lines.append(f"{s}\t{lib[s]}\t{detected[s]}\t"
                            f"{'fail' if s in failing else 'pass'}")

    keep = [s for s in samples if s not in failing]
    cpm = {s: {g: counts[s][g] * 1e6 / lib[s] for g in genes} for s in keep}
    kept_genes = [g for g in genes
                  if sum(1 for s in keep if cpm[s][g] >= 1.0) >= 3]
    gene_lines = ["gene\tn_samples_expressed\tmean_cpm"]
    for g in kept_genes:
        n_exp = sum(1 for s in keep if cpm[s][g] >= 1.0)
        gene_lines.append(f"{g}\t{n_exp}\t{sum(cpm[s][g] for s in keep) / len(keep):.4f}")

    summary_lines = ["metric\tvalue"]
    summary_lines.append(f"n_samples_total\t{len(samples)}")
    summary_lines.append(f"n_samples_passing\t{len(keep)}")
    summary_lines.append(f"n_genes_total\t{len(genes)}")
    summary_lines.append(f"n_genes_retained\t{len(kept_genes)}")
    summary_lines.append(f"median_library_size\t{median_lib:.1f}")

    outputs = {
        "/app/output/sample_qc.tsv": "\n".join(sample_lines) + "\n",
        "/app/output/gene_filter.tsv": "\n".join(gene_lines) + "\n",
        "/app/output/summary.tsv": "\n".join(summary_lines) + "\n",
    }

    instruction = """
    `/app/data/counts.tsv` is a gene-by-sample RNA-seq count matrix: 4000 genes
    down the rows, 12 samples across the columns.

    Produce **three** files in `/app/output`. All three are graded.

    `sample_qc.tsv`, header `sample\tlibrary_size\tn_detected\tstatus`, one row
    per sample in input column order. `library_size` is that sample's total
    count, `n_detected` its number of genes with a count above zero. A sample's
    `status` is `fail` when its library size is below 30% of the median library
    size across all 12 samples, or when fewer than 1200 genes are detected;
    otherwise `pass`.

    `gene_filter.tsv`, header `gene\tn_samples_expressed\tmean_cpm`, computed
    over the passing samples only. CPM is a gene's count divided by that
    sample's library size, times one million. Keep a gene when at least three
    passing samples have CPM of 1.0 or more. `mean_cpm` is the gene's mean CPM
    across all passing samples, to four decimals. Keep input gene order.

    `summary.tsv`, header `metric\tvalue`, with rows `n_samples_total`,
    `n_samples_passing`, `n_genes_total`, `n_genes_retained` and
    `median_library_size` in that order, the last to one decimal.
    """

    solve = r"""#!/usr/bin/env bash
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
"""
    write_multi_task(name, "rnaseq", ["counts", "qc", "filtering", "multi-output"],
                     instruction, outputs, solve, tol=1e-3)
    print(f"  {name}: {len(failing)} failing samples, {len(kept_genes)} genes retained")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    gen_kmer_index(root)
    gen_gc_bias(root)
    gen_multi_qc(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
