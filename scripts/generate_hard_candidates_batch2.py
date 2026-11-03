#!/usr/bin/env python3
"""Generate v1.0 hard candidates, batch 2. Runs inside bioterm-base:v1.

    docker run --rm -v "$PWD":/repo -w /repo bioterm-base:v1 \
        python3 scripts/generate_hard_candidates_batch2.py
"""

from __future__ import annotations

import random
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hard_candidate_common import write_task  # noqa: E402

import pysam  # noqa: E402


# ------------------------------------------------- 4. phased haplotype blocks
def gen_phase_blocks(root: Path) -> None:
    name = "vcf-phase-blocks"
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(90210)

    header = [
        "##fileformat=VCFv4.2",
        '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
        '##FORMAT=<ID=PS,Number=1,Type=Integer,Description="Phase set">',
        "##contig=<ID=chr1,length=3000000>",
        "##contig=<ID=chr2,length=3000000>",
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE",
    ]
    body = []
    blocks: dict[tuple[str, int], list[int]] = defaultdict(list)

    for chrom in ("chr1", "chr2"):
        p = rng.randrange(10_000, 30_000)
        for _ in range(rng.randrange(5, 8)):
            ps = p
            n = rng.randrange(1, 9)          # some blocks have a single variant
            for _ in range(n):
                p += rng.randrange(120, 4000)
                gt = rng.choice(["0|1", "1|0"])
                body.append(f"{chrom}\t{p}\t.\tA\tG\t60\tPASS\t.\tGT:PS\t{gt}:{ps}")
                blocks[(chrom, ps)].append(p)
            # Unphased and homozygous records carry no PS and must be ignored.
            for _ in range(rng.randrange(1, 4)):
                p += rng.randrange(120, 2000)
                gt = rng.choice(["0/1", "1/1", "0|0"])
                body.append(f"{chrom}\t{p}\t.\tA\tG\t60\tPASS\t.\tGT\t{gt}")
            p += rng.randrange(5000, 20_000)

    order = {"chr1": 0, "chr2": 1}
    body.sort(key=lambda ln: (order[ln.split("\t")[0]], int(ln.split("\t")[1])))
    vcf = d / "phased.vcf"
    vcf.write_text("\n".join(header + body) + "\n")
    subprocess.run(["bgzip", "-f", str(vcf)], check=True)
    subprocess.run(["tabix", "-p", "vcf", str(vcf) + ".gz"], check=True)

    rows = []
    for (chrom, ps), positions in blocks.items():
        if len(positions) < 2:
            continue
        positions.sort()
        gaps = [b - a for a, b in zip(positions, positions[1:])]
        rows.append((chrom, ps, len(positions), positions[0], positions[-1],
                     positions[-1] - positions[0] + 1, max(gaps)))
    rows.sort(key=lambda r: (order[r[0]], r[1]))
    lines = ["chrom\tphase_set\tn_variants\tstart\tend\tspan\tmax_gap"]
    lines += ["\t".join(map(str, r)) for r in rows]
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/phased.vcf.gz` (with `.tbi`) is a single-sample VCF. Some records
    carry a phased genotype and a `PS` (phase set) value; others are unphased or
    homozygous and carry no `PS`.

    Summarise the haplotype blocks.

    Use only records whose genotype is **phased and heterozygous** -- the `GT`
    separator is `|` and the two alleles differ -- and which have a `PS` value.
    A block is all such records sharing a chromosome and a `PS` value.

    Report only blocks holding at least two variants.

    Write `/app/output/phase_blocks.tsv` with header

    `chrom\tphase_set\tn_variants\tstart\tend\tspan\tmax_gap`

    where `start` and `end` are the smallest and largest positions in the block,
    `span` is `end - start + 1`, and `max_gap` is the largest difference between
    consecutive positions in the block. Sort by chromosome (`chr1` before
    `chr2`) then ascending `phase_set`.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
import gzip
from collections import defaultdict

order = {"chr1": 0, "chr2": 1}
blocks = defaultdict(list)
with gzip.open("/app/data/phased.vcf.gz", "rt") as fh:
    for line in fh:
        if line.startswith("#"):
            continue
        f = line.rstrip("\n").split("\t")
        keys, vals = f[8].split(":"), f[9].split(":")
        s = dict(zip(keys, vals))
        gt = s.get("GT", "")
        if "|" not in gt or "PS" not in s:
            continue
        a, b = gt.split("|")
        if a == b:
            continue
        blocks[(f[0], int(s["PS"]))].append(int(f[1]))

rows = []
for (chrom, ps), pos in blocks.items():
    if len(pos) < 2:
        continue
    pos.sort()
    gaps = [y - x for x, y in zip(pos, pos[1:])]
    rows.append((chrom, ps, len(pos), pos[0], pos[-1], pos[-1] - pos[0] + 1, max(gaps)))

rows.sort(key=lambda r: (order[r[0]], r[1]))
with open("/app/output/phase_blocks.tsv", "w") as fh:
    fh.write("chrom\tphase_set\tn_variants\tstart\tend\tspan\tmax_gap\n")
    for r in rows:
        fh.write("\t".join(map(str, r)) + "\n")
PY
"""
    write_task(name, "variant", ["vcf", "phasing", "haplotype", "blocks"],
               instruction, expected, solve, "/app/output/phase_blocks.tsv")
    print(f"  {name}: {len(rows)} blocks")


# ------------------------------------------------------------ 5. UMI dedup
def gen_umi_dedup(root: Path) -> None:
    name = "fastq-umi-dedup"
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(5150)

    umis = ["ACGTAC", "TTGCAA", "GGCATT", "CATGGA", "TACCGT"]
    reads = []
    rid = 0
    for umi in umis:
        for _ in range(rng.randrange(3, 7)):
            core = "".join(rng.choice("ACGT") for _ in range(20))
            for _ in range(rng.randrange(1, 5)):     # duplicates of this molecule
                rid += 1
                tail = "".join(rng.choice("ACGT") for _ in range(30))
                quals = "".join(chr(33 + rng.randrange(20, 41)) for _ in range(50))
                reads.append((f"read{rid:04d}", umi, core + tail, quals))

    rng.shuffle(reads)
    with (d / "reads.fastq").open("w") as fh:
        for name_, umi, seq, q in reads:
            fh.write(f"@{name_}_UMI:{umi}\n{seq}\n+\n{q}\n")

    groups = defaultdict(list)
    for name_, umi, seq, q in reads:
        groups[(umi, seq[:20])].append((name_, q))

    per_umi = defaultdict(lambda: [0, 0, []])
    for (umi, _core), members in groups.items():
        best = sorted(members, key=lambda m: (-sum(ord(c) - 33 for c in m[1]) / len(m[1]), m[0]))[0]
        per_umi[umi][0] += len(members)
        per_umi[umi][1] += 1
        per_umi[umi][2].append(best[0])

    lines = ["umi\tn_reads\tn_kept\tkept_ids"]
    for umi in sorted(per_umi):
        n_reads, n_kept, kept = per_umi[umi]
        lines.append(f"{umi}\t{n_reads}\t{n_kept}\t{','.join(sorted(kept))}")
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/reads.fastq` holds 50-base reads. Each read name ends with
    `_UMI:` followed by a six-base UMI, as in `@read0001_UMI:ACGTAC`.

    Collapse PCR duplicates and summarise per UMI.

    Two reads are duplicates of the same molecule when they share **both** the
    UMI and the **first 20 bases** of the sequence. From each such group keep
    exactly one read: the one with the highest mean base quality (Phred, ASCII
    minus 33, averaged over all 50 bases). If several tie, keep the one whose
    read name sorts first lexicographically.

    Write `/app/output/dedup.tsv` with header

    `umi\tn_reads\tn_kept\tkept_ids`

    one row per UMI sorted lexicographically, where `n_reads` is how many reads
    carry that UMI, `n_kept` is how many molecules survive, and `kept_ids` is
    the comma-separated list of kept read names (without the `_UMI:` suffix)
    sorted lexicographically, with no spaces.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
from collections import defaultdict

groups = defaultdict(list)
per_umi_reads = defaultdict(int)
with open("/app/data/reads.fastq") as fh:
    while True:
        h = fh.readline()
        if not h:
            break
        seq = fh.readline().strip()
        fh.readline()
        qual = fh.readline().strip()
        name, umi = h[1:].strip().split("_UMI:")
        groups[(umi, seq[:20])].append((name, qual))
        per_umi_reads[umi] += 1

kept = defaultdict(list)
for (umi, _core), members in groups.items():
    best = sorted(members, key=lambda m: (-sum(ord(c) - 33 for c in m[1]) / len(m[1]), m[0]))[0]
    kept[umi].append(best[0])

with open("/app/output/dedup.tsv", "w") as fh:
    fh.write("umi\tn_reads\tn_kept\tkept_ids\n")
    for umi in sorted(kept):
        ids = sorted(kept[umi])
        fh.write(f"{umi}\t{per_umi_reads[umi]}\t{len(ids)}\t{','.join(ids)}\n")
PY
"""
    write_task(name, "qc", ["fastq", "umi", "duplicates", "quality"],
               instruction, expected, solve, "/app/output/dedup.tsv")
    print(f"  {name}: {len(groups)} molecules across {len(per_umi)} UMIs")


# ------------------------------------------------------ 6. synteny blocks
def gen_synteny(root: Path) -> None:
    name = "ortholog-synteny-blocks"
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(6180)

    pairs = []          # (chrA, idxA, chrB, idxB)
    plan = [("A1", "B1", 9, +1), ("A1", "B1", 6, -1), ("A2", "B3", 11, +1),
            ("A2", "B2", 4, +1), ("A3", "B2", 7, -1), ("A3", "B4", 2, +1)]
    a_idx = defaultdict(int)
    b_idx = defaultdict(int)
    for chrA, chrB, n, sign in plan:
        b_start = b_idx[chrB] + rng.randrange(5, 15)
        for k in range(n):
            a_idx[chrA] += rng.randrange(1, 3)
            bi = b_start + (k if sign > 0 else n - 1 - k) * rng.randrange(1, 3)
            pairs.append((chrA, a_idx[chrA], chrB, bi))
        b_idx[chrB] = max(b_idx[chrB], b_start + n * 3)
        a_idx[chrA] += rng.randrange(20, 40)      # break the chain

    rng.shuffle(pairs)
    with (d / "orthologs.tsv").open("w") as fh:
        fh.write("gene_a\tchrom_a\tindex_a\tgene_b\tchrom_b\tindex_b\n")
        for i, (ca, ia, cb, ib) in enumerate(pairs, start=1):
            fh.write(f"gA{i:04d}\t{ca}\t{ia}\tgB{i:04d}\t{cb}\t{ib}\n")

    # Reference chaining.
    by_chrom = defaultdict(list)
    for ca, ia, cb, ib in pairs:
        by_chrom[ca].append((ia, cb, ib))
    rows = []
    for ca in sorted(by_chrom):
        items = sorted(by_chrom[ca])
        cur = [items[0]]
        for prev, nxt in zip(items, items[1:]):
            same_b = nxt[1] == prev[1]
            step = nxt[2] - prev[2]
            cont = same_b and 1 <= abs(step) <= 3 and (
                len(cur) == 1 or (step > 0) == (cur[-1][2] - cur[-2][2] > 0))
            if cont:
                cur.append(nxt)
            else:
                if len(cur) >= 3:
                    rows.append((ca, cur))
                cur = [nxt]
        if len(cur) >= 3:
            rows.append((ca, cur))

    out = []
    for ca, chain in rows:
        cb = chain[0][1]
        orient = "+" if chain[-1][2] > chain[0][2] else "-"
        out.append((ca, cb, orient, len(chain), chain[0][0], chain[-1][0]))
    out.sort(key=lambda r: (r[0], r[4]))
    lines = ["chrom_a\tchrom_b\torientation\tn_pairs\tstart_a\tend_a"]
    lines += ["\t".join(map(str, r)) for r in out]
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/orthologs.tsv` lists one-to-one ortholog pairs between two
    genomes, with each gene's chromosome and its integer order index along that
    chromosome. The rows are shuffled.

    Chain the pairs into syntenic blocks.

    Work through each genome-A chromosome in ascending `index_a`. Two
    consecutive pairs continue the same block when they map to the **same**
    genome-B chromosome and their `index_b` values differ by at least 1 and at
    most 3. A block must keep a consistent direction: once a block has two
    members, every later step must have the same sign of `index_b` change as the
    step before it. Any pair that fails these tests starts a new block.

    Report only blocks containing at least three pairs.

    Write `/app/output/synteny_blocks.tsv` with header

    `chrom_a\tchrom_b\torientation\tn_pairs\tstart_a\tend_a`

    where `orientation` is `+` when `index_b` rises across the block and `-`
    when it falls, and `start_a`/`end_a` are the first and last `index_a`.
    Sort by `chrom_a` then `start_a`.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
from collections import defaultdict

by_chrom = defaultdict(list)
with open("/app/data/orthologs.tsv") as fh:
    next(fh)
    for line in fh:
        _ga, ca, ia, _gb, cb, ib = line.rstrip("\n").split("\t")
        by_chrom[ca].append((int(ia), cb, int(ib)))

blocks = []
for ca in sorted(by_chrom):
    items = sorted(by_chrom[ca])
    cur = [items[0]]
    for prev, nxt in zip(items, items[1:]):
        step = nxt[2] - prev[2]
        cont = nxt[1] == prev[1] and 1 <= abs(step) <= 3 and (
            len(cur) == 1 or (step > 0) == (cur[-1][2] - cur[-2][2] > 0))
        if cont:
            cur.append(nxt)
        else:
            if len(cur) >= 3:
                blocks.append((ca, cur))
            cur = [nxt]
    if len(cur) >= 3:
        blocks.append((ca, cur))

rows = []
for ca, chain in blocks:
    orient = "+" if chain[-1][2] > chain[0][2] else "-"
    rows.append((ca, chain[0][1], orient, len(chain), chain[0][0], chain[-1][0]))
rows.sort(key=lambda r: (r[0], r[4]))

with open("/app/output/synteny_blocks.tsv", "w") as fh:
    fh.write("chrom_a\tchrom_b\torientation\tn_pairs\tstart_a\tend_a\n")
    for r in rows:
        fh.write("\t".join(map(str, r)) + "\n")
PY
"""
    write_task(name, "search", ["orthologs", "synteny", "chaining"],
               instruction, expected, solve, "/app/output/synteny_blocks.tsv")
    print(f"  {name}: {len(out)} blocks from {len(pairs)} pairs")


# --------------------------------------------------- 7. soft-clip breakpoints
def gen_softclip(root: Path) -> None:
    name = "bam-softclip-breakpoints"
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(24680)

    refs = [("chr1", 300_000)]
    header = {"HD": {"VN": "1.6", "SO": "coordinate"},
              "SQ": [{"SN": n, "LN": ln} for n, ln in refs]}
    records = []
    support = defaultdict(list)
    qi = 0

    def add(pos, cigar, *, flag=0, clip_side=None, clip_len=0):
        nonlocal qi
        qi += 1
        a = pysam.AlignedSegment()
        a.query_name = f"sc{qi:05d}"
        rlen = sum(n for op, n in cigar if op in (0, 4))
        a.query_sequence = "A" * rlen
        a.query_qualities = pysam.qualitystring_to_array("I" * rlen)
        a.cigartuples = cigar
        a.reference_id = 0
        a.reference_start = pos
        a.mapping_quality = 60
        a.flag = flag
        records.append(a)
        if clip_side and clip_len >= 10 and not (flag & (0x100 | 0x400 | 0x800 | 0x4)):
            bp = pos if clip_side == "L" else pos + sum(n for op, n in cigar if op == 0)
            support[("chr1", clip_side)].append(bp)

    for centre in (50_000, 120_000, 200_000):
        for _ in range(rng.randrange(4, 8)):        # left-clip cluster
            jitter = rng.randrange(-2, 3)
            clip = rng.randrange(12, 30)
            add(centre + jitter, [(4, clip), (0, 100 - clip)], clip_side="L", clip_len=clip)
        for _ in range(rng.randrange(3, 6)):        # right-clip cluster
            jitter = rng.randrange(-2, 3)
            clip = rng.randrange(11, 28)
            add(centre + 400 + jitter, [(0, 100 - clip), (4, clip)],
                clip_side="R", clip_len=clip)

    for _ in range(25):                              # clean reads
        add(rng.randrange(1000, 280_000), [(0, 100)])
    for _ in range(10):                              # clips too short to count
        s = rng.randrange(1000, 280_000)
        add(s, [(4, rng.randrange(3, 10)), (0, 94)], clip_side="L", clip_len=5)
    for _ in range(6):                               # excluded by flags
        add(70_000, [(4, 20), (0, 80)], flag=0x100, clip_side="L", clip_len=20)
        add(70_000, [(4, 20), (0, 80)], flag=0x400, clip_side="L", clip_len=20)

    records.sort(key=lambda a: a.reference_start)
    tmp = d / "clips.unsorted.bam"
    with pysam.AlignmentFile(str(tmp), "wb", header=header) as out:
        for a in records:
            out.write(a)
    pysam.sort("-o", str(d / "clips.bam"), str(tmp))
    pysam.index(str(d / "clips.bam"))
    tmp.unlink()

    def cluster(points: list[int]) -> list[list[int]]:
        points = sorted(points)
        groups, cur = [], [points[0]]
        for p in points[1:]:
            if p - cur[-1] <= 5:
                cur.append(p)
            else:
                groups.append(cur)
                cur = [p]
        groups.append(cur)
        return groups

    rows = []
    for (chrom, side), pts in support.items():
        for g in cluster(pts):
            if len(g) >= 3:
                g_sorted = sorted(g)
                med = g_sorted[(len(g_sorted) - 1) // 2]      # lower median
                rows.append((chrom, side, med, len(g)))
    rows.sort(key=lambda r: (r[0], r[2], r[1]))
    lines = ["chrom\tside\tposition\tn_reads"]
    lines += ["\t".join(map(str, r)) for r in rows]
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/clips.bam` (indexed) contains 100-base alignments, some of them
    soft-clipped at a breakpoint.

    Find the breakpoints that several reads agree on.

    Use only alignments that are mapped and are not secondary (`0x100`), not
    supplementary (`0x800`) and not duplicates (`0x400`). An alignment
    contributes a breakpoint when its CIGAR begins or ends with a soft clip
    (`S`) of **at least 10 bases**:

    - a leading clip gives a `L` breakpoint at the alignment's leftmost
      reference position;
    - a trailing clip gives a `R` breakpoint one base past the last aligned
      reference base.

    Use 0-based reference positions, as `samtools` reports them internally.

    Cluster breakpoints that share a chromosome and side and lie within 5 bases
    of the previous position in the sorted cluster. Report only clusters with at
    least three supporting reads.

    Write `/app/output/breakpoints.tsv` with header

    `chrom\tside\tposition\tn_reads`

    where `position` is the cluster's median, taking the lower of the two middle
    values when the count is even. Sort by chromosome, then position, then side.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
import pysam
from collections import defaultdict

support = defaultdict(list)
bam = pysam.AlignmentFile("/app/data/clips.bam", "rb")
for a in bam:
    if a.flag & (0x100 | 0x800 | 0x400 | 0x4):
        continue
    ct = a.cigartuples or []
    if not ct:
        continue
    chrom = bam.get_reference_name(a.reference_id)
    if ct[0][0] == 4 and ct[0][1] >= 10:
        support[(chrom, "L")].append(a.reference_start)
    if ct[-1][0] == 4 and ct[-1][1] >= 10:
        support[(chrom, "R")].append(a.reference_start + sum(n for op, n in ct if op == 0))

rows = []
for (chrom, side), pts in support.items():
    pts = sorted(pts)
    cur = [pts[0]]
    groups = []
    for p in pts[1:]:
        if p - cur[-1] <= 5:
            cur.append(p)
        else:
            groups.append(cur); cur = [p]
    groups.append(cur)
    for g in groups:
        if len(g) >= 3:
            rows.append((chrom, side, sorted(g)[(len(g) - 1) // 2], len(g)))

rows.sort(key=lambda r: (r[0], r[2], r[1]))
with open("/app/output/breakpoints.tsv", "w") as fh:
    fh.write("chrom\tside\tposition\tn_reads\n")
    for r in rows:
        fh.write("\t".join(map(str, r)) + "\n")
PY
"""
    write_task(name, "alignment", ["bam", "cigar", "softclip", "breakpoints"],
               instruction, expected, solve, "/app/output/breakpoints.tsv")
    print(f"  {name}: {len(rows)} breakpoint clusters")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    gen_phase_blocks(root)
    gen_umi_dedup(root)
    gen_synteny(root)
    gen_softclip(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
