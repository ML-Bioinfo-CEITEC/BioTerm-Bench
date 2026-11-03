#!/usr/bin/env python3
"""Generate v1.0 hard candidates, batch 4 -- classical algorithms and statistics.

Batches 1-3 are read-the-file-carefully tasks, and the screening panel solved
them on the first attempt, 27B model included. These six ask for a textbook
method to be implemented exactly: dynamic programming with affine gaps,
Viterbi in log space, Fisher plus Benjamini-Hochberg, weighted interval
scheduling, Fitch parsimony, and EM for haplotype frequencies. The work is no
longer clerical, and several have a numerical trap -- Viterbi underflows to
zero if a model multiplies probabilities instead of adding logs.

    docker run --rm -v "$PWD":/repo -w /repo bioterm-base:v1 \
        python3 scripts/generate_hard_candidates_batch4.py
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hard_candidate_common import write_task  # noqa: E402


# ------------------------------------------------------ 11. affine-gap global
def gen_affine(root: Path) -> None:
    name = "align-affine-gap-score"
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(112233)
    MATCH, MISMATCH, OPEN, EXTEND, LINEAR = 2, -3, 10, 1, 4

    def mutate(s: str) -> str:
        out = []
        i = 0
        while i < len(s):
            r = rng.random()
            if r < 0.06:                       # substitution
                out.append(rng.choice([b for b in "ACGT" if b != s[i]]))
                i += 1
            elif r < 0.09:                     # deletion of a short run
                i += rng.randrange(2, 7)
            elif r < 0.12:                     # insertion of a short run
                out.append("".join(rng.choice("ACGT") for _ in range(rng.randrange(2, 7))))
                out.append(s[i])
                i += 1
            else:
                out.append(s[i])
                i += 1
        return "".join(out)

    pairs = []
    for p in range(1, 6):
        a = "".join(rng.choice("ACGT") for _ in range(rng.randrange(120, 161)))
        pairs.append((f"pair{p}", a, mutate(a)))

    with (d / "pairs.fasta").open("w") as fh:
        for pid, a, b in pairs:
            fh.write(f">{pid}_a\n{a}\n>{pid}_b\n{b}\n")

    NEG = float("-inf")

    def affine(x: str, y: str) -> int:
        n, m = len(x), len(y)
        M = [[NEG] * (m + 1) for _ in range(n + 1)]
        X = [[NEG] * (m + 1) for _ in range(n + 1)]
        Y = [[NEG] * (m + 1) for _ in range(n + 1)]
        M[0][0] = 0
        for i in range(1, n + 1):
            X[i][0] = -OPEN - EXTEND * i
        for j in range(1, m + 1):
            Y[0][j] = -OPEN - EXTEND * j
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                s = MATCH if x[i - 1] == y[j - 1] else MISMATCH
                M[i][j] = max(M[i - 1][j - 1], X[i - 1][j - 1], Y[i - 1][j - 1]) + s
                X[i][j] = max(M[i - 1][j] - OPEN - EXTEND, X[i - 1][j] - EXTEND,
                              Y[i - 1][j] - OPEN - EXTEND)
                Y[i][j] = max(M[i][j - 1] - OPEN - EXTEND, Y[i][j - 1] - EXTEND,
                              X[i][j - 1] - OPEN - EXTEND)
        return int(max(M[n][m], X[n][m], Y[n][m]))

    def linear(x: str, y: str) -> int:
        n, m = len(x), len(y)
        prev = [-LINEAR * j for j in range(m + 1)]
        for i in range(1, n + 1):
            cur = [-LINEAR * i] + [0] * m
            for j in range(1, m + 1):
                s = MATCH if x[i - 1] == y[j - 1] else MISMATCH
                cur[j] = max(prev[j - 1] + s, prev[j] - LINEAR, cur[j - 1] - LINEAR)
            prev = cur
        return int(prev[m])

    lines = ["pair_id\tlen_a\tlen_b\tscore_affine\tscore_linear"]
    for pid, a, b in pairs:
        lines.append(f"{pid}\t{len(a)}\t{len(b)}\t{affine(a, b)}\t{linear(a, b)}")
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/pairs.fasta` holds five sequence pairs, named `pair1_a` and
    `pair1_b` through `pair5_a` and `pair5_b`.

    Score the optimal **global** alignment of each pair under two gap models.
    Report scores only, not alignments.

    Both models score a match `+2` and a mismatch `-3`, and both penalise gaps
    at the ends of the alignment exactly as gaps in the middle.

    - `score_affine`: a gap of length `L` costs `10 + L`, so opening costs 10
      and every gap position costs a further 1.
    - `score_linear`: a gap of length `L` costs `4 * L`.

    A higher score is better and the penalties are subtracted. Report the score
    of the best alignment, which for these sequences is not the same alignment
    under the two models.

    Write `/app/output/alignment_scores.tsv` with header

    `pair_id\tlen_a\tlen_b\tscore_affine\tscore_linear`

    one row per pair in `pair1`..`pair5` order, where `len_a` and `len_b` are
    the input sequence lengths and both scores are integers.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
MATCH, MISMATCH, OPEN, EXTEND, LINEAR = 2, -3, 10, 1, 4
NEG = float("-inf")

seqs, name, buf = {}, None, []
for line in open("/app/data/pairs.fasta"):
    if line.startswith(">"):
        if name:
            seqs[name] = "".join(buf)
        name, buf = line[1:].strip(), []
    else:
        buf.append(line.strip())
if name:
    seqs[name] = "".join(buf)


def affine(x, y):
    n, m = len(x), len(y)
    M = [[NEG] * (m + 1) for _ in range(n + 1)]
    X = [[NEG] * (m + 1) for _ in range(n + 1)]
    Y = [[NEG] * (m + 1) for _ in range(n + 1)]
    M[0][0] = 0
    for i in range(1, n + 1):
        X[i][0] = -OPEN - EXTEND * i
    for j in range(1, m + 1):
        Y[0][j] = -OPEN - EXTEND * j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            s = MATCH if x[i - 1] == y[j - 1] else MISMATCH
            M[i][j] = max(M[i - 1][j - 1], X[i - 1][j - 1], Y[i - 1][j - 1]) + s
            X[i][j] = max(M[i - 1][j] - OPEN - EXTEND, X[i - 1][j] - EXTEND,
                          Y[i - 1][j] - OPEN - EXTEND)
            Y[i][j] = max(M[i][j - 1] - OPEN - EXTEND, Y[i][j - 1] - EXTEND,
                          X[i][j - 1] - OPEN - EXTEND)
    return int(max(M[n][m], X[n][m], Y[n][m]))


def linear(x, y):
    n, m = len(x), len(y)
    prev = [-LINEAR * j for j in range(m + 1)]
    for i in range(1, n + 1):
        cur = [-LINEAR * i] + [0] * m
        for j in range(1, m + 1):
            s = MATCH if x[i - 1] == y[j - 1] else MISMATCH
            cur[j] = max(prev[j - 1] + s, prev[j] - LINEAR, cur[j - 1] - LINEAR)
        prev = cur
    return int(prev[m])


with open("/app/output/alignment_scores.tsv", "w") as fh:
    fh.write("pair_id\tlen_a\tlen_b\tscore_affine\tscore_linear\n")
    for p in range(1, 6):
        a, b = seqs[f"pair{p}_a"], seqs[f"pair{p}_b"]
        fh.write(f"pair{p}\t{len(a)}\t{len(b)}\t{affine(a, b)}\t{linear(a, b)}\n")
PY
"""
    write_task(name, "alignment", ["dynamic-programming", "affine-gap", "global-alignment"],
               instruction, expected, solve, "/app/output/alignment_scores.tsv")
    print(f"  {name}: {len(pairs)} pairs")


# ------------------------------------------------------------- 12. Viterbi
def gen_viterbi(root: Path) -> None:
    name = "hmm-viterbi-segments"
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(20260824)

    states = ["AT_rich", "GC_rich"]
    init = {"AT_rich": 0.6, "GC_rich": 0.4}
    trans = {"AT_rich": {"AT_rich": 0.985, "GC_rich": 0.015},
             "GC_rich": {"AT_rich": 0.030, "GC_rich": 0.970}}
    emit = {"AT_rich": {"A": 0.32, "C": 0.18, "G": 0.18, "T": 0.32},
            "GC_rich": {"A": 0.15, "C": 0.35, "G": 0.35, "T": 0.15}}

    with (d / "model.tsv").open("w") as fh:
        fh.write("state\tinit\tto_AT_rich\tto_GC_rich\te_A\te_C\te_G\te_T\n")
        for s in states:
            fh.write(f"{s}\t{init[s]:.4f}\t{trans[s]['AT_rich']:.4f}\t"
                     f"{trans[s]['GC_rich']:.4f}\t"
                     + "\t".join(f"{emit[s][b]:.4f}" for b in "ACGT") + "\n")

    cur = "AT_rich" if rng.random() < init["AT_rich"] else "GC_rich"
    seq = []
    for _ in range(4000):
        r, acc = rng.random(), 0.0
        for b in "ACGT":
            acc += emit[cur][b]
            if r <= acc:
                seq.append(b)
                break
        else:
            seq.append("T")
        cur = "AT_rich" if rng.random() < trans[cur]["AT_rich"] else "GC_rich"
    seq = "".join(seq)
    with (d / "sequence.fasta").open("w") as fh:
        fh.write(">contig1\n")
        for i in range(0, len(seq), 60):
            fh.write(seq[i:i + 60] + "\n")

    lg = math.log
    delta = {s: lg(init[s]) + lg(emit[s][seq[0]]) for s in states}
    back = []
    for base in seq[1:]:
        step, nxt = {}, {}
        for s in states:
            best = max(states, key=lambda p: (delta[p] + lg(trans[p][s]), -states.index(p)))
            nxt[s] = delta[best] + lg(trans[best][s]) + lg(emit[s][base])
            step[s] = best
        back.append(step)
        delta = nxt
    last = max(states, key=lambda s: (delta[s], -states.index(s)))
    path = [last]
    for step in reversed(back):
        path.append(step[path[-1]])
    path.reverse()

    rows, start = [], 0
    for i in range(1, len(path) + 1):
        if i == len(path) or path[i] != path[start]:
            rows.append((start + 1, i, path[start], i - start))
            start = i
    lines = ["start\tend\tstate\tlength"]
    lines += ["\t".join(map(str, r)) for r in rows]
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/sequence.fasta` holds one 4000-base sequence.
    `/app/data/model.tsv` gives a two-state HMM: each row is a state with its
    initial probability, its transition probabilities to `AT_rich` and
    `GC_rich`, and its emission probabilities for A, C, G and T.

    Decode the sequence with the **Viterbi** algorithm and report the state
    segments.

    Work in log space. Multiplying 4000 probabilities underflows to zero in
    double precision and silently produces a wrong path.

    Should two states ever tie exactly, prefer the one listed first in
    `model.tsv`.

    Collapse the decoded path into maximal runs of one state.

    Write `/app/output/segments.tsv` with header

    `start\tend\tstate\tlength`

    one row per run, in ascending `start`, where `start` and `end` are 1-based
    inclusive positions along the sequence and `length` is `end - start + 1`.
    The runs must tile the whole sequence with no gap and no overlap.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
import math

seq = "".join(l.strip() for l in open("/app/data/sequence.fasta") if not l.startswith(">"))

states, init, trans, emit = [], {}, {}, {}
rows = [l.rstrip("\n").split("\t") for l in open("/app/data/model.tsv")]
hdr = rows[0]
for r in rows[1:]:
    s = r[0]
    states.append(s)
    init[s] = float(r[1])
    trans[s] = {"AT_rich": float(r[2]), "GC_rich": float(r[3])}
    emit[s] = {b: float(r[hdr.index("e_" + b)]) for b in "ACGT"}

lg = math.log
delta = {s: lg(init[s]) + lg(emit[s][seq[0]]) for s in states}
back = []
for base in seq[1:]:
    step, nxt = {}, {}
    for s in states:
        best = max(states, key=lambda p: (delta[p] + lg(trans[p][s]), -states.index(p)))
        nxt[s] = delta[best] + lg(trans[best][s]) + lg(emit[s][base])
        step[s] = best
    back.append(step)
    delta = nxt

last = max(states, key=lambda s: (delta[s], -states.index(s)))
path = [last]
for step in reversed(back):
    path.append(step[path[-1]])
path.reverse()

with open("/app/output/segments.tsv", "w") as fh:
    fh.write("start\tend\tstate\tlength\n")
    start = 0
    for i in range(1, len(path) + 1):
        if i == len(path) or path[i] != path[start]:
            fh.write(f"{start + 1}\t{i}\t{path[start]}\t{i - start}\n")
            start = i
PY
"""
    write_task(name, "search", ["hmm", "viterbi", "segmentation", "log-space"],
               instruction, expected, solve, "/app/output/segments.tsv")
    print(f"  {name}: {len(rows)} segments over 4000 bp")


# ------------------------------------------------ 13. Fisher exact + BH FDR
def gen_fisher(root: Path) -> None:
    from scipy.stats import fisher_exact

    name = "counts-fisher-bh-fdr"
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)

    def build(seed: int):
        """One fixture attempt. Returns None if any gene lands near q = 0.05."""
        rng = random.Random(seed)
        genes, pvals = [], []
        i = 0
        while len(genes) < 400:
            i += 1
            gene = f"GENE{i:04d}"
            if rng.random() < 0.10:                   # genuinely different
                a = rng.randrange(40, 120)
                b = rng.randrange(2, 20)
            else:
                base = rng.randrange(10, 90)
                a = max(base + rng.randrange(-6, 7), 0)
                b = max(base + rng.randrange(-6, 7), 0)
            c = rng.randrange(10, 90)
            e = rng.randrange(10, 90)
            genes.append((gene, a, b, c, e))
            pvals.append(fisher_exact([[a, b], [c, e]])[1])

        n = len(pvals)
        order = sorted(range(n), key=lambda k: (pvals[k], genes[k][0]))
        q = [0.0] * n
        running = 1.0
        for rank in range(n, 0, -1):
            k = order[rank - 1]
            running = min(running, pvals[k] * n / rank)
            q[k] = running
        # Any correct two-sided Fisher exact test (scipy's, R's) agrees to well
        # under 1e-9, so only a gene sitting *on* the 0.05 line could flip the
        # answer for an irrelevant reason. Reject such a fixture.
        if any(0.0495 < v < 0.0505 for v in q):
            return None
        return genes, pvals, q, order

    built = None
    for seed in range(606060, 606260):
        built = build(seed)
        if built is not None:
            break
    if built is None:
        raise SystemExit(f"{name}: no seed gave a fixture clear of the q=0.05 boundary")
    genes, pvals, q, order = built
    n = len(pvals)

    with (d / "counts.tsv").open("w") as fh:
        fh.write("gene\talt_case\tref_case\talt_control\tref_control\n")
        for gene, a, b, c, e in genes:
            fh.write(f"{gene}\t{a}\t{b}\t{c}\t{e}\n")

    sig = [k for k in order if q[k] < 0.05]
    lines = ["gene\talt_case\tref_case\talt_control\tref_control\tp_value\tq_value"]
    for k in sig:
        g, a, b, c, e = genes[k]
        lines.append(f"{g}\t{a}\t{b}\t{c}\t{e}\t{pvals[k]:.6e}\t{q[k]:.6e}")
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/counts.tsv` gives, for each of 400 genes, four counts:
    `alt_case`, `ref_case`, `alt_control`, `ref_control`.

    Test each gene for an association between allele and group, then control
    the false discovery rate.

    For each gene run a **two-sided Fisher exact test** on the 2x2 table whose
    first row is `[alt_case, ref_case]` and whose second row is
    `[alt_control, ref_control]`.

    Adjust the 400 p-values with the **Benjamini-Hochberg** procedure: rank
    them ascending, set `q = p * 400 / rank`, then enforce monotonicity by
    walking from the largest rank down and replacing each `q` with the smallest
    `q` seen so far at or above it. Keep only genes with `q < 0.05`.

    Write `/app/output/significant.tsv` with header

    `gene\talt_case\tref_case\talt_control\tref_control\tp_value\tq_value`

    one row per significant gene, sorted by ascending `p_value` and then by
    gene name, echoing the four input counts and giving `p_value` and
    `q_value` in scientific notation with six decimals, as `1.234567e-05`.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
from scipy.stats import fisher_exact

rows = []
with open("/app/data/counts.tsv") as fh:
    next(fh)
    for line in fh:
        g, a, b, c, e = line.rstrip("\n").split("\t")
        rows.append((g, int(a), int(b), int(c), int(e)))

p = [fisher_exact([[r[1], r[2]], [r[3], r[4]]])[1] for r in rows]
n = len(p)
order = sorted(range(n), key=lambda k: (p[k], rows[k][0]))
q = [0.0] * n
running = 1.0
for rank in range(n, 0, -1):
    k = order[rank - 1]
    running = min(running, p[k] * n / rank)
    q[k] = running

with open("/app/output/significant.tsv", "w") as fh:
    fh.write("gene\talt_case\tref_case\talt_control\tref_control\tp_value\tq_value\n")
    for k in order:
        if q[k] >= 0.05:
            continue
        g, a, b, c, e = rows[k]
        fh.write(f"{g}\t{a}\t{b}\t{c}\t{e}\t{p[k]:.6e}\t{q[k]:.6e}\n")
PY
"""
    write_task(name, "rnaseq", ["statistics", "fisher-exact", "fdr", "multiple-testing"],
               instruction, expected, solve, "/app/output/significant.tsv")
    print(f"  {name}: {len(sig)} significant of {n} genes")


# ---------------------------------------- 14. weighted interval scheduling
def gen_scheduling(root: Path) -> None:
    name = "interval-weighted-scheduling"
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(97531)

    rows = []
    per_chrom: dict[str, list[tuple[int, int, float]]] = {}
    for c in range(1, 7):
        chrom = f"chr{c}"
        items = []
        for _ in range(500):
            start = rng.randrange(0, 400_000)
            end = start + rng.randrange(200, 9000)
            score = round(rng.uniform(1.0, 400.0), 2)
            items.append((start, end, score))
        per_chrom[chrom] = items
        rows.extend((chrom, s, e, sc) for s, e, sc in items)
    rng.shuffle(rows)
    with (d / "intervals.tsv").open("w") as fh:
        fh.write("chrom\tstart\tend\tscore\n")
        for chrom, s, e, sc in rows:
            fh.write(f"{chrom}\t{s}\t{e}\t{sc:.2f}\n")

    import bisect

    out = []
    for chrom in sorted(per_chrom):
        items = sorted(per_chrom[chrom], key=lambda t: (t[1], t[0]))
        ends = [t[1] for t in items]
        best = [0.0] * (len(items) + 1)
        for i, (s, _e, sc) in enumerate(items, start=1):
            j = bisect.bisect_right(ends, s, 0, i - 1)
            best[i] = max(best[i - 1], best[j] + sc)
        out.append((chrom, len(items), best[len(items)]))
    lines = ["chrom\tn_intervals\tmax_score"]
    lines += [f"{c}\t{n}\t{v:.2f}" for c, n, v in out]
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/intervals.tsv` lists scored intervals on six chromosomes, in
    shuffled order, with half-open coordinates: an interval covers `start` up
    to but not including `end`.

    For each chromosome, choose a set of intervals that do not overlap each
    other and whose total score is as large as possible, and report that total.

    Two intervals do not overlap when one's `end` is less than or equal to the
    other's `start`, so intervals that merely touch may both be chosen. Every
    chromosome is independent. Scores are positive, so the empty set is never
    the best answer.

    Five hundred intervals per chromosome is far too many to enumerate subsets
    of; solve it exactly rather than greedily. Sorting by `end` and keeping,
    for each interval, the best total achievable up to it gives the answer in
    near-linear time. A greedy choice by score, or by earliest end, does not.

    Write `/app/output/best_sets.tsv` with header

    `chrom\tn_intervals\tmax_score`

    one row per chromosome sorted by name, where `n_intervals` is how many
    intervals that chromosome has in the input and `max_score` is the best
    total to two decimals.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
import bisect
from collections import defaultdict

per = defaultdict(list)
with open("/app/data/intervals.tsv") as fh:
    next(fh)
    for line in fh:
        chrom, s, e, sc = line.rstrip("\n").split("\t")
        per[chrom].append((int(s), int(e), float(sc)))

with open("/app/output/best_sets.tsv", "w") as fh:
    fh.write("chrom\tn_intervals\tmax_score\n")
    for chrom in sorted(per):
        items = sorted(per[chrom], key=lambda t: (t[1], t[0]))
        ends = [t[1] for t in items]
        best = [0.0] * (len(items) + 1)
        for i, (s, _e, sc) in enumerate(items, start=1):
            j = bisect.bisect_right(ends, s, 0, i - 1)
            best[i] = max(best[i - 1], best[j] + sc)
        fh.write(f"{chrom}\t{len(items)}\t{best[len(items)]:.2f}\n")
PY
"""
    write_task(name, "search", ["dynamic-programming", "intervals", "optimisation"],
               instruction, expected, solve, "/app/output/best_sets.tsv", tol=1e-2)
    print(f"  {name}: {len(out)} chromosomes x 500 intervals")


# ------------------------------------------------------- 15. Fitch parsimony
def gen_fitch(root: Path) -> None:
    name = "phylo-fitch-parsimony"
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(13579)

    taxa = [f"T{i}" for i in range(1, 11)]
    newick = "(((T1,T2),(T3,(T4,T5))),((T6,T7),(T8,(T9,T10))));"
    (d / "tree.newick").write_text(newick + "\n")

    n_sites = 150
    cols = []
    for _ in range(n_sites):
        base = rng.choice("ACGT")
        col = {t: base for t in taxa}
        for t in taxa:
            if rng.random() < 0.18:
                col[t] = rng.choice([b for b in "ACGT" if b != base])
        cols.append(col)
    with (d / "alignment.fasta").open("w") as fh:
        for t in taxa:
            s = "".join(c[t] for c in cols)
            fh.write(f">{t}\n")
            for i in range(0, len(s), 60):
                fh.write(s[i:i + 60] + "\n")

    def parse(nw: str):
        pos = 0

        def node():
            nonlocal pos
            if nw[pos] == "(":
                pos += 1
                kids = [node()]
                while nw[pos] == ",":
                    pos += 1
                    kids.append(node())
                pos += 1                       # ')'
                return kids
            start = pos
            while nw[pos] not in ",()":
                pos += 1
            return nw[start:pos]

        return node()

    tree = parse(newick.rstrip(";\n"))

    def fitch(node, col):
        if isinstance(node, str):
            return {col[node]}, 0
        sets, cost = [], 0
        for kid in node:
            s, c = fitch(kid, col)
            sets.append(s)
            cost += c
        inter = set.intersection(*sets)
        if inter:
            return inter, cost
        return set.union(*sets), cost + 1

    lines = ["site\tn_distinct_bases\tparsimony_score"]
    total = 0
    for i, col in enumerate(cols, start=1):
        _s, cost = fitch(tree, col)
        total += cost
        lines.append(f"{i}\t{len(set(col.values()))}\t{cost}")
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/tree.newick` is a rooted binary tree over ten taxa with no
    branch lengths. `/app/data/alignment.fasta` holds those ten taxa aligned
    over 150 sites, all bases A, C, G or T with no gaps.

    Compute the **Fitch parsimony** score of every site on this tree.

    Fitch works bottom-up. Each leaf's state set is the single base that taxon
    has at the site. At an internal node, take the intersection of its
    children's state sets: if the intersection is non-empty, that is the node's
    set and no change is counted; if it is empty, the node's set is the union
    and the score increases by one. A site's score is the total number of
    changes counted over the whole tree.

    Write `/app/output/parsimony.tsv` with header

    `site\tn_distinct_bases\tparsimony_score`

    one row for every site, in ascending site number counting from 1, where
    `n_distinct_bases` is how many different bases appear among the ten taxa at
    that site and `parsimony_score` is the Fitch score. Include sites scoring
    zero.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
seqs, name, buf = {}, None, []
for line in open("/app/data/alignment.fasta"):
    if line.startswith(">"):
        if name:
            seqs[name] = "".join(buf)
        name, buf = line[1:].strip(), []
    else:
        buf.append(line.strip())
if name:
    seqs[name] = "".join(buf)

nw = open("/app/data/tree.newick").read().strip().rstrip(";")
pos = 0


def node():
    global pos
    if nw[pos] == "(":
        pos += 1
        kids = [node()]
        while nw[pos] == ",":
            pos += 1
            kids.append(node())
        pos += 1
        return kids
    start = pos
    while pos < len(nw) and nw[pos] not in ",()":
        pos += 1
    return nw[start:pos]


tree = node()


def fitch(n, i):
    if isinstance(n, str):
        return {seqs[n][i]}, 0
    sets, cost = [], 0
    for kid in n:
        s, c = fitch(kid, i)
        sets.append(s)
        cost += c
    inter = set.intersection(*sets)
    if inter:
        return inter, cost
    return set.union(*sets), cost + 1


n_sites = len(next(iter(seqs.values())))
with open("/app/output/parsimony.tsv", "w") as fh:
    fh.write("site\tn_distinct_bases\tparsimony_score\n")
    for i in range(n_sites):
        _s, cost = fitch(tree, i)
        distinct = len({s[i] for s in seqs.values()})
        fh.write(f"{i + 1}\t{distinct}\t{cost}\n")
PY
"""
    write_task(name, "search", ["phylogenetics", "parsimony", "fitch", "newick"],
               instruction, expected, solve, "/app/output/parsimony.tsv")
    print(f"  {name}: {n_sites} sites, total parsimony {total}")


# --------------------------------------------- 16. EM haplotype frequencies
def gen_em(root: Path) -> None:
    name = "popgen-haplotype-em"
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(864213)

    HAPS = ["0-0", "0-1", "1-0", "1-1"]
    pairs = {}
    lines_in = []
    for p in range(1, 6):
        true_f = [rng.uniform(0.1, 1.0) for _ in range(4)]
        tot = sum(true_f)
        true_f = [x / tot for x in true_f]
        people = []
        for s in range(1, 201):
            picks = []
            for _ in range(2):
                r, acc = rng.random(), 0.0
                for h, f in zip(HAPS, true_f):
                    acc += f
                    if r <= acc:
                        picks.append(h)
                        break
                else:
                    picks.append(HAPS[-1])
            g1 = sum(int(h[0]) for h in picks)
            g2 = sum(int(h[2]) for h in picks)
            people.append((f"pair{p}_ind{s:03d}", g1, g2))
            lines_in.append((f"pair{p}", f"pair{p}_ind{s:03d}", g1, g2))
        pairs[f"pair{p}"] = people

    with (d / "genotypes.tsv").open("w") as fh:
        fh.write("pair_id\tsample\tn_alt_locus1\tn_alt_locus2\n")
        for row in lines_in:
            fh.write("\t".join(map(str, row)) + "\n")

    def em(people):
        f = {h: 0.25 for h in HAPS}
        for _ in range(200):
            counts = {h: 0.0 for h in HAPS}
            for _s, g1, g2 in people:
                if g1 == 1 and g2 == 1:
                    p1 = 2 * f["0-0"] * f["1-1"]
                    p2 = 2 * f["0-1"] * f["1-0"]
                    tot = p1 + p2
                    w1 = 0.5 if tot == 0 else p1 / tot
                    counts["0-0"] += w1
                    counts["1-1"] += w1
                    counts["0-1"] += 1 - w1
                    counts["1-0"] += 1 - w1
                    continue
                a1 = [0, 0] if g1 == 0 else ([0, 1] if g1 == 1 else [1, 1])
                a2 = [0, 0] if g2 == 0 else ([0, 1] if g2 == 1 else [1, 1])
                counts[f"{a1[0]}-{a2[0]}"] += 1
                counts[f"{a1[1]}-{a2[1]}"] += 1
            n = sum(counts.values())
            f = {h: counts[h] / n for h in HAPS}
        return f

    lines = ["pair_id\thaplotype\tfrequency"]
    for pid in sorted(pairs):
        f = em(pairs[pid])
        for h in HAPS:
            lines.append(f"{pid}\t{h}\t{f[h]:.6f}")
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/genotypes.tsv` gives, for five independent locus pairs, 200
    individuals each with their unphased genotypes at two biallelic loci as an
    alternate-allele count of 0, 1 or 2.

    Estimate the four haplotype frequencies for each locus pair by **EM**.

    Label haplotypes `0-0`, `0-1`, `1-0`, `1-1` by their alleles at locus 1 and
    locus 2. Every genotype combination determines an individual's two
    haplotypes uniquely except the double heterozygote (1 and 1), which is
    either `0-0` plus `1-1` or `0-1` plus `1-0`.

    Start every frequency at `0.25` and run exactly **200 iterations**. In each
    iteration, split each double heterozygote between the two possibilities in
    proportion to `2*f(0-0)*f(1-1)` and `2*f(0-1)*f(1-0)` using the current
    frequencies, then set each new frequency to that haplotype's expected count
    divided by 400.

    Write `/app/output/haplotype_freqs.tsv` with header

    `pair_id\thaplotype\tfrequency`

    twenty rows, sorted by `pair_id` then by haplotype in the order above,
    frequencies to six decimals.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
from collections import defaultdict

HAPS = ["0-0", "0-1", "1-0", "1-1"]
per = defaultdict(list)
with open("/app/data/genotypes.tsv") as fh:
    next(fh)
    for line in fh:
        pid, _s, g1, g2 = line.rstrip("\n").split("\t")
        per[pid].append((int(g1), int(g2)))

with open("/app/output/haplotype_freqs.tsv", "w") as fh:
    fh.write("pair_id\thaplotype\tfrequency\n")
    for pid in sorted(per):
        f = {h: 0.25 for h in HAPS}
        for _ in range(200):
            counts = {h: 0.0 for h in HAPS}
            for g1, g2 in per[pid]:
                if g1 == 1 and g2 == 1:
                    p1 = 2 * f["0-0"] * f["1-1"]
                    p2 = 2 * f["0-1"] * f["1-0"]
                    tot = p1 + p2
                    w1 = 0.5 if tot == 0 else p1 / tot
                    counts["0-0"] += w1
                    counts["1-1"] += w1
                    counts["0-1"] += 1 - w1
                    counts["1-0"] += 1 - w1
                    continue
                a1 = [0, 0] if g1 == 0 else ([0, 1] if g1 == 1 else [1, 1])
                a2 = [0, 0] if g2 == 0 else ([0, 1] if g2 == 1 else [1, 1])
                counts[f"{a1[0]}-{a2[0]}"] += 1
                counts[f"{a1[1]}-{a2[1]}"] += 1
            n = sum(counts.values())
            f = {h: counts[h] / n for h in HAPS}
        for h in HAPS:
            fh.write(f"{pid}\t{h}\t{f[h]:.6f}\n")
PY
"""
    write_task(name, "variant", ["population-genetics", "em", "haplotype", "linkage"],
               instruction, expected, solve, "/app/output/haplotype_freqs.tsv", tol=1e-5)
    print(f"  {name}: 5 locus pairs x 200 individuals")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    gen_affine(root)
    gen_viterbi(root)
    gen_fisher(root)
    gen_scheduling(root)
    gen_fitch(root)
    gen_em(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
