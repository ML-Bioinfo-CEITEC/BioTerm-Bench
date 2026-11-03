#!/usr/bin/env python3
"""Generate v1.0 hard candidates, batch 3 -- algorithmic tasks.

Batches 1 and 2 are parsing-and-bookkeeping tasks, and the strongest model in
the screening panel solved them on the first attempt. These three ask for a
named algorithm to be implemented correctly rather than a file to be read
carefully, which is where the failure modes stop being clerical.

    docker run --rm -v "$PWD":/repo -w /repo bioterm-base:v1 \
        python3 scripts/generate_hard_candidates_batch3.py
"""

from __future__ import annotations

import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hard_candidate_common import write_task  # noqa: E402


# ------------------------------------------------- 8. de Bruijn graph unitigs
def gen_unitigs(root: Path) -> None:
    name = "kmer-debruijn-unitigs"
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(31337)
    K = 21

    def seq(n: int) -> str:
        return "".join(rng.choice("ACGT") for _ in range(n))

    # A shared 40-base repeat forces the graph to branch, so the answer is
    # several unitigs rather than one contig.
    repeat = seq(40)
    genome = seq(300) + repeat + seq(250) + repeat + seq(280)

    reads = []
    pos = 0
    while pos + 120 <= len(genome):
        reads.append(genome[pos:pos + 120])
        pos += rng.randrange(14, 26)
    reads.append(genome[-120:])
    rng.shuffle(reads)
    with (d / "reads.fasta").open("w") as fh:
        for i, r in enumerate(reads, start=1):
            fh.write(f">read{i:04d}\n{r}\n")

    def unitigs(reads: list[str], k: int) -> list[str]:
        kmers = set()
        for r in reads:
            for i in range(len(r) - k + 1):
                kmers.add(r[i:i + k])
        outs, ins = defaultdict(set), defaultdict(set)
        for km in kmers:
            outs[km[:-1]].add(km[1:])
            ins[km[1:]].add(km[:-1])
        simple = {n for n in set(outs) | set(ins)
                  if len(outs.get(n, ())) == 1 and len(ins.get(n, ())) == 1}
        seen, out = set(), []
        for km in kmers:
            u, v = km[:-1], km[1:]
            if u in simple and (u, next(iter(outs[u]))) == (u, v):
                # This edge is interior to some unitig unless u is a start.
                pass
            # Start an edge-path only where the left node cannot be interior.
            if u in simple:
                continue
            path = [u, v]
            e = (u, v)
            if e in seen:
                continue
            seen.add(e)
            cur = v
            while cur in simple:
                nxt = next(iter(outs[cur]))
                seen.add((cur, nxt))
                path.append(nxt)
                cur = nxt
            out.append(path[0] + "".join(p[-1] for p in path[1:]))
        # Edges whose left node is simple but that were never reached belong to
        # cycles; the reference genome is linear so none should remain.
        for km in kmers:
            if (km[:-1], km[1:]) not in seen:
                raise SystemExit(f"{name}: unreachable edge -- fixture has a cycle")
        return out

    seqs = unitigs(reads, K)
    rows = sorted(((len(s), s) for s in seqs), key=lambda t: (-t[0], t[1]))
    lines = ["unitig_id\tlength\tn_kmers\tsequence"]
    for i, (ln, s) in enumerate(rows, start=1):
        lines.append(f"unitig{i:03d}\t{ln}\t{ln - K + 1}\t{s}")
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/reads.fasta` holds error-free 120-base reads, all from the
    forward strand of one linear sequence.

    Build a de Bruijn graph with **k = 21** and report its unitigs.

    Nodes are the distinct 20-mers; every distinct 21-mer in the reads is one
    edge, from its first 20 bases to its last 20. Ignore reverse complements
    and count each distinct 21-mer once.

    Call a node **simple** when it has exactly one incoming and exactly one
    outgoing edge. A unitig is a maximal path of edges whose every *interior*
    node is simple; each edge belongs to exactly one unitig. Spell a unitig by
    taking its first node's 20 bases and then the final base of each edge along
    the path.

    Write `/app/output/unitigs.tsv` with header

    `unitig_id\tlength\tn_kmers\tsequence`

    sorted by descending `length`, ties broken by ascending `sequence`. Number
    them `unitig001`, `unitig002`, ... in that order. `n_kmers` is the number of
    edges in the unitig.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
from collections import defaultdict

K = 21
reads, cur = [], []
for line in open("/app/data/reads.fasta"):
    if line.startswith(">"):
        if cur:
            reads.append("".join(cur)); cur = []
    else:
        cur.append(line.strip())
if cur:
    reads.append("".join(cur))

kmers = set()
for r in reads:
    for i in range(len(r) - K + 1):
        kmers.add(r[i:i + K])

outs, ins = defaultdict(set), defaultdict(set)
for km in kmers:
    outs[km[:-1]].add(km[1:])
    ins[km[1:]].add(km[:-1])

simple = {n for n in set(outs) | set(ins)
          if len(outs.get(n, ())) == 1 and len(ins.get(n, ())) == 1}

seqs, seen = [], set()
for km in sorted(kmers):
    u, v = km[:-1], km[1:]
    if u in simple or (u, v) in seen:
        continue
    seen.add((u, v))
    path = [u, v]
    cur_node = v
    while cur_node in simple:
        nxt = next(iter(outs[cur_node]))
        seen.add((cur_node, nxt))
        path.append(nxt)
        cur_node = nxt
    seqs.append(path[0] + "".join(p[-1] for p in path[1:]))

rows = sorted(seqs, key=lambda s: (-len(s), s))
with open("/app/output/unitigs.tsv", "w") as fh:
    fh.write("unitig_id\tlength\tn_kmers\tsequence\n")
    for i, s in enumerate(rows, start=1):
        fh.write(f"unitig{i:03d}\t{len(s)}\t{len(s) - K + 1}\t{s}\n")
PY
"""
    write_task(name, "search", ["kmer", "de-bruijn", "assembly", "graph"],
               instruction, expected, solve, "/app/output/unitigs.tsv")
    print(f"  {name}: {len(rows)} unitigs from {len(reads)} reads")


# ------------------------------------------------------ 9. neighbour joining
def gen_nj(root: Path) -> None:
    name = "phylo-neighbor-joining"
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(4242)

    taxa = ["Anser", "Bufo", "Canis", "Danio", "Equus", "Felis", "Gallus", "Homo"]
    coords = {t: [rng.uniform(0, 10) for _ in range(3)] for t in taxa}
    dist: dict[tuple[str, str], float] = {}
    for i, a in enumerate(taxa):
        for b in taxa[i + 1:]:
            v = sum(abs(x - y) for x, y in zip(coords[a], coords[b]))
            v = round(v + rng.uniform(0, 0.4), 4)
            dist[(a, b)] = dist[(b, a)] = v
    for t in taxa:
        dist[(t, t)] = 0.0

    with (d / "distances.tsv").open("w") as fh:
        fh.write("taxon\t" + "\t".join(taxa) + "\n")
        for a in taxa:
            fh.write(a + "\t" + "\t".join(f"{dist[(a, b)]:.4f}" for b in taxa) + "\n")

    def neighbor_join(names: list[str], dm: dict) -> list[tuple]:
        names = list(names)
        dm = dict(dm)
        steps = []
        counter = 0
        while len(names) > 2:
            n = len(names)
            total = {x: sum(dm[(x, y)] for y in names if y != x) for x in names}
            best = None
            for i, a in enumerate(names):
                for b in names[i + 1:]:
                    q = (n - 2) * dm[(a, b)] - total[a] - total[b]
                    key = (round(q, 9),) + tuple(sorted((a, b)))
                    if best is None or key < best[0]:
                        best = (key, a, b)
            _, a, b = best
            delta = (total[a] - total[b]) / (n - 2)
            la = 0.5 * dm[(a, b)] + 0.5 * delta
            lb = dm[(a, b)] - la
            counter += 1
            u = f"N{counter}"
            lengths = dict(zip(sorted((a, b)), (la, lb) if a < b else (lb, la)))
            first, second = sorted((a, b))
            steps.append((counter, first, second, lengths[first], lengths[second]))
            for k in names:
                if k in (a, b):
                    continue
                dm[(u, k)] = dm[(k, u)] = 0.5 * (dm[(a, k)] + dm[(b, k)] - dm[(a, b)])
            dm[(u, u)] = 0.0
            names = [x for x in names if x not in (a, b)] + [u]
        a, b = sorted(names)
        steps.append((counter + 1, a, b, dm[(a, b)], 0.0))
        return steps

    steps = neighbor_join(taxa, dist)
    lines = ["step\tnode_a\tnode_b\tlen_a\tlen_b"]
    for s, a, b, la, lb in steps:
        lines.append(f"{s}\t{a}\t{b}\t{la:.4f}\t{lb:.4f}")
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/distances.tsv` is a symmetric distance matrix over eight taxa,
    with the taxon names in the header row and the first column.

    Run **neighbour joining** on it and report every join.

    At each step, with `n` nodes remaining and `R(x)` the sum of `x`'s distances
    to all other current nodes, compute
    `Q(a,b) = (n-2)*d(a,b) - R(a) - R(b)` for every pair and join the pair with
    the smallest `Q`. Break ties by taking the pair whose two names, sorted
    lexicographically, come first. The branch lengths are
    `L(a) = d(a,b)/2 + (R(a)-R(b)) / (2*(n-2))` and `L(b) = d(a,b) - L(a)`.
    The new node's distance to each remaining node `k` is
    `(d(a,k) + d(b,k) - d(a,b)) / 2`. Name new nodes `N1`, `N2`, ... in join
    order and repeat until two nodes remain.

    Write `/app/output/nj_steps.tsv` with header

    `step\tnode_a\tnode_b\tlen_a\tlen_b`

    one row per join, `step` counting from 1, the two names in lexicographic
    order with their own lengths, all lengths to four decimals. Add one final
    row for the last two nodes with `len_a` their distance and `len_b` `0.0000`.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
rows = [ln.rstrip("\n").split("\t") for ln in open("/app/data/distances.tsv")]
names = rows[0][1:]
dm = {}
for r in rows[1:]:
    for j, name in enumerate(names):
        dm[(r[0], name)] = float(r[j + 1])

steps, counter = [], 0
while len(names) > 2:
    n = len(names)
    total = {x: sum(dm[(x, y)] for y in names if y != x) for x in names}
    best = None
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            q = (n - 2) * dm[(a, b)] - total[a] - total[b]
            key = (round(q, 9),) + tuple(sorted((a, b)))
            if best is None or key < best[0]:
                best = (key, a, b)
    _, a, b = best
    la = dm[(a, b)] / 2 + (total[a] - total[b]) / (2 * (n - 2))
    lb = dm[(a, b)] - la
    counter += 1
    u = f"N{counter}"
    lens = {a: la, b: lb}
    first, second = sorted((a, b))
    steps.append((counter, first, second, lens[first], lens[second]))
    for k in list(names):
        if k in (a, b):
            continue
        dm[(u, k)] = dm[(k, u)] = (dm[(a, k)] + dm[(b, k)] - dm[(a, b)]) / 2
    dm[(u, u)] = 0.0
    names = [x for x in names if x not in (a, b)] + [u]

a, b = sorted(names)
steps.append((counter + 1, a, b, dm[(a, b)], 0.0))

with open("/app/output/nj_steps.tsv", "w") as fh:
    fh.write("step\tnode_a\tnode_b\tlen_a\tlen_b\n")
    for s, x, y, lx, ly in steps:
        fh.write(f"{s}\t{x}\t{y}\t{lx:.4f}\t{ly:.4f}\n")
PY
"""
    write_task(name, "search", ["distance-matrix", "neighbor-joining", "tree"],
               instruction, expected, solve, "/app/output/nj_steps.tsv")
    print(f"  {name}: {len(steps)} joins over {len(taxa)} taxa")


# ------------------------------------------------- 10. coordinate remap + check
def gen_remap(root: Path) -> None:
    name = "vcf-remap-verify"
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(778899)
    COMP = str.maketrans("ACGT", "TGCA")

    new_ref = {"new1": "".join(rng.choice("ACGT") for _ in range(6000)),
               "new2": "".join(rng.choice("ACGT") for _ in range(6000))}
    with (d / "new_reference.fa").open("w") as fh:
        for chrom, s in new_ref.items():
            fh.write(f">{chrom}\n")
            for i in range(0, len(s), 60):
                fh.write(s[i:i + 60] + "\n")

    # (old_chrom, old_start, old_end, new_chrom, new_start, strand)
    blocks = [
        ("old1", 1, 1200, "new1", 501, "+"),
        ("old1", 2001, 2800, "new1", 3001, "-"),
        ("old2", 1, 900, "new2", 101, "-"),
        ("old2", 1501, 2400, "new2", 2001, "+"),
    ]
    with (d / "blocks.tsv").open("w") as fh:
        fh.write("old_chrom\told_start\told_end\tnew_chrom\tnew_start\tstrand\n")
        for b in blocks:
            fh.write("\t".join(map(str, b)) + "\n")

    def remap(old_chrom, old_pos):
        for oc, os_, oe, nc, ns, strand in blocks:
            if oc == old_chrom and os_ <= old_pos <= oe:
                if strand == "+":
                    return nc, ns + (old_pos - os_), "+"
                return nc, ns + (oe - old_pos), "-"
        return None

    records, expected_rows = [], []
    for _ in range(34):
        old_chrom = rng.choice(["old1", "old2"])
        old_pos = rng.randrange(1, 3200)
        hit = remap(old_chrom, old_pos)
        if hit is None:
            ref, alt = rng.choice("ACGT"), rng.choice("ACGT")
            while alt == ref:
                alt = rng.choice("ACGT")
            records.append((old_chrom, old_pos, ref, alt))
            expected_rows.append((old_chrom, old_pos, ".", ".", ".", ".", "unmapped"))
            continue
        nc, np_, strand = hit
        base = new_ref[nc][np_ - 1]
        true_old_ref = base if strand == "+" else base.translate(COMP)
        broken = rng.random() < 0.25
        if broken:
            ref = rng.choice([b for b in "ACGT" if b != true_old_ref])
        else:
            ref = true_old_ref
        alt = rng.choice([b for b in "ACGT" if b != ref])
        records.append((old_chrom, old_pos, ref, alt))
        new_alt = alt if strand == "+" else alt.translate(COMP)
        status = "ref_mismatch" if broken else "mapped"
        expected_rows.append((old_chrom, old_pos, nc, str(np_), base, new_alt, status))

    order = {"old1": 0, "old2": 1}
    paired = sorted(zip(records, expected_rows), key=lambda p: (order[p[0][0]], p[0][1]))
    records = [p[0] for p in paired]
    expected_rows = [p[1] for p in paired]

    header = ["##fileformat=VCFv4.2", "##contig=<ID=old1,length=3200>",
              "##contig=<ID=old2,length=3200>",
              "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO"]
    with (d / "variants.vcf").open("w") as fh:
        fh.write("\n".join(header) + "\n")
        for c, p, r, a in records:
            fh.write(f"{c}\t{p}\t.\t{r}\t{a}\t50\tPASS\t.\n")

    lines = ["old_chrom\told_pos\tnew_chrom\tnew_pos\tnew_ref\tnew_alt\tstatus"]
    lines += ["\t".join(map(str, r)) for r in expected_rows]
    expected = "\n".join(lines) + "\n"

    instruction = """
    Three inputs in `/app/data`: `variants.vcf` (SNVs on an old assembly),
    `blocks.tsv` (alignment blocks between the assemblies) and
    `new_reference.fa` (the new assembly).

    Lift every variant over and check it against the new reference.

    Each block gives `old_chrom old_start old_end new_chrom new_start strand`,
    all 1-based inclusive, and blocks do not overlap. For a variant at
    `old_pos` inside a block, the new position is
    `new_start + (old_pos - old_start)` on a `+` block and
    `new_start + (old_end - old_pos)` on a `-` block. On a `-` block the
    alleles are complemented (A<->T, C<->G).

    `new_ref` is the base actually present at that new position in
    `new_reference.fa`. A variant is `mapped` when `new_ref` equals the lifted
    REF, and `ref_mismatch` when it does not. A variant inside no block is
    `unmapped`.

    Write `/app/output/remapped.tsv` with header

    `old_chrom\told_pos\tnew_chrom\tnew_pos\tnew_ref\tnew_alt\tstatus`

    one row per input variant in input order, using `.` for all four new
    columns of an `unmapped` variant.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
COMP = str.maketrans("ACGT", "TGCA")

ref = {}
name = None
buf = []
for line in open("/app/data/new_reference.fa"):
    if line.startswith(">"):
        if name:
            ref[name] = "".join(buf)
        name, buf = line[1:].strip().split()[0], []
    else:
        buf.append(line.strip())
if name:
    ref[name] = "".join(buf)

blocks = []
with open("/app/data/blocks.tsv") as fh:
    next(fh)
    for line in fh:
        oc, os_, oe, nc, ns, strand = line.rstrip("\n").split("\t")
        blocks.append((oc, int(os_), int(oe), nc, int(ns), strand))

out = ["old_chrom\told_pos\tnew_chrom\tnew_pos\tnew_ref\tnew_alt\tstatus"]
for line in open("/app/data/variants.vcf"):
    if line.startswith("#"):
        continue
    f = line.rstrip("\n").split("\t")
    chrom, pos, r, a = f[0], int(f[1]), f[3], f[4]
    hit = None
    for oc, os_, oe, nc, ns, strand in blocks:
        if oc == chrom and os_ <= pos <= oe:
            np_ = ns + (pos - os_) if strand == "+" else ns + (oe - pos)
            hit = (nc, np_, strand)
            break
    if hit is None:
        out.append(f"{chrom}\t{pos}\t.\t.\t.\t.\tunmapped")
        continue
    nc, np_, strand = hit
    lifted_ref = r if strand == "+" else r.translate(COMP)
    lifted_alt = a if strand == "+" else a.translate(COMP)
    actual = ref[nc][np_ - 1]
    status = "mapped" if actual == lifted_ref else "ref_mismatch"
    out.append(f"{chrom}\t{pos}\t{nc}\t{np_}\t{actual}\t{lifted_alt}\t{status}")

open("/app/output/remapped.tsv", "w").write("\n".join(out) + "\n")
PY
"""
    write_task(name, "variant", ["vcf", "liftover", "reference", "strand"],
               instruction, expected, solve, "/app/output/remapped.tsv")
    n_mis = sum(1 for r in expected_rows if r[6] == "ref_mismatch")
    n_un = sum(1 for r in expected_rows if r[6] == "unmapped")
    print(f"  {name}: {len(expected_rows)} variants "
          f"({n_mis} ref_mismatch, {n_un} unmapped)")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    gen_unitigs(root)
    gen_nj(root)
    gen_remap(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
