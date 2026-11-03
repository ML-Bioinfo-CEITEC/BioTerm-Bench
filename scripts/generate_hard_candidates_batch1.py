#!/usr/bin/env python3
"""Generate v1.0 hard candidates, batch 1. Runs inside bioterm-base:v1.

Each task is deliberately *integrative*: the difficulty is in getting several
coupled steps exactly right, not in a hidden formatting trap. Every fixture is
built from a fixed seed and every expected answer is computed here by a
reference implementation, so the task and its key cannot drift apart.

    docker run --rm -v "$PWD":/repo -w /repo bioterm-base:v1 \
        python3 scripts/generate_hard_candidates_batch1.py
"""

from __future__ import annotations

import random
import subprocess
import sys
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hard_candidate_common import write_task  # noqa: E402

import pysam  # noqa: E402


# ---------------------------------------------------------------- helpers
def med1(values: list[int]) -> str:
    """Median of |TLEN|, one decimal, mean-of-middle-two on even counts."""
    return f"{median(values):.1f}" if values else "0.0"


# ------------------------------------------------- 1. pair orientation stats
def gen_pair_orientation(root: Path) -> None:
    name = "bam-pair-orientation-stats"
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(20260824)

    refs = [("chr1", 200_000), ("chr2", 150_000)]
    header = {"HD": {"VN": "1.6", "SO": "coordinate"},
              "SQ": [{"SN": n, "LN": ln} for n, ln in refs]}

    # (orientation, count) for pairs that must be counted, plus decoys that must
    # not be: secondary, supplementary, duplicate, mate-unmapped, cross-contig.
    plan = [("FR", 46), ("RF", 19), ("TANDEM", 27)]
    records = []
    counted: dict[str, list[int]] = {"FR": [], "RF": [], "TANDEM": []}
    qi = 0

    def add_pair(ref_id, pos1, pos2, r1_rev, r2_rev, *, flags_extra1=0,
                 flags_extra2=0, count=True, orientation=None, mate_ref=None):
        nonlocal qi
        qi += 1
        qname = f"rd{qi:05d}"
        rlen = 100
        tlen = (pos2 + rlen) - pos1 if pos2 >= pos1 else (pos2 - (pos1 + rlen))
        mref = ref_id if mate_ref is None else mate_ref
        for is_r1, (pos, rev, mpos, mrev, extra) in enumerate([
            (pos1, r1_rev, pos2, r2_rev, flags_extra1),
            (pos2, r2_rev, pos1, r1_rev, flags_extra2),
        ]):
            a = pysam.AlignedSegment()
            a.query_name = qname
            a.query_sequence = "A" * rlen
            a.query_qualities = pysam.qualitystring_to_array("I" * rlen)
            a.cigarstring = f"{rlen}M"
            a.reference_id = ref_id
            a.reference_start = pos
            a.next_reference_id = mref
            a.next_reference_start = mpos
            a.mapping_quality = 60
            flag = 0x1 | 0x2
            flag |= 0x40 if is_r1 == 0 else 0x80
            if rev:
                flag |= 0x10
            if mrev:
                flag |= 0x20
            flag |= extra
            a.flag = flag
            a.template_length = tlen if is_r1 == 0 else -tlen
            records.append(a)
        if count and orientation:
            counted[orientation].append(abs(tlen))

    for orientation, n in plan:
        for _ in range(n):
            start = rng.randrange(1000, 190_000)
            gap = rng.randrange(50, 600)
            pos1, pos2 = start, start + gap
            if orientation == "FR":
                add_pair(0, pos1, pos2, False, True, orientation="FR")
            elif orientation == "RF":
                add_pair(0, pos1, pos2, True, False, orientation="RF")
            else:
                rev = rng.random() < 0.5
                add_pair(1, pos1, pos2, rev, rev, orientation="TANDEM")

    # Decoys -- each must be excluded by exactly one rule in the contract.
    for _ in range(9):    # secondary
        s = rng.randrange(1000, 100_000)
        add_pair(0, s, s + 300, False, True, flags_extra1=0x100, count=False)
    for _ in range(7):    # supplementary
        s = rng.randrange(1000, 100_000)
        add_pair(0, s, s + 300, False, True, flags_extra1=0x800, count=False)
    for _ in range(8):    # PCR duplicate
        s = rng.randrange(1000, 100_000)
        add_pair(0, s, s + 300, False, True, flags_extra1=0x400,
                 flags_extra2=0x400, count=False)
    for _ in range(6):    # mate unmapped
        s = rng.randrange(1000, 100_000)
        add_pair(0, s, s + 300, False, True, flags_extra1=0x8, count=False)
    for _ in range(5):    # cross-contig
        s = rng.randrange(1000, 100_000)
        add_pair(0, s, s + 300, False, True, count=False, mate_ref=1)

    records.sort(key=lambda a: (a.reference_id, a.reference_start))
    tmp = d / "pairs.unsorted.bam"
    with pysam.AlignmentFile(str(tmp), "wb", header=header) as out:
        for a in records:
            out.write(a)
    pysam.sort("-o", str(d / "pairs.bam"), str(tmp))
    pysam.index(str(d / "pairs.bam"))
    tmp.unlink()

    lines = ["orientation\tn_pairs\tmedian_abs_tlen"]
    for o in ("FR", "RF", "TANDEM"):
        lines.append(f"{o}\t{len(counted[o])}\t{med1(counted[o])}")
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/pairs.bam` (indexed) holds paired-end alignments over two contigs.

    Classify read pairs by relative orientation and summarise each class.

    Count each pair once, from its **read1** record only, and only if that
    record is: paired (`0x1`), proper pair (`0x2`), read1 (`0x40`), not
    secondary (`0x100`), not supplementary (`0x800`), not duplicate (`0x400`),
    itself mapped (not `0x4`), mate mapped (not `0x8`), and mate on the same
    reference.

    Orientation comes from the two strand flags:

    - `TANDEM` if read and mate are on the same strand;
    - otherwise find the leftmost read by position (`POS` vs `PNEXT`; on a tie
      treat read1 as leftmost). It is `FR` if that leftmost read is forward,
      `RF` if it is reverse.

    Write `/app/output/pair_orientation.tsv` with header

    `orientation	n_pairs	median_abs_tlen`

    and exactly three rows in the order `FR`, `RF`, `TANDEM`.
    `median_abs_tlen` is the median of `abs(TLEN)` over the counted read1
    records to one decimal, using the mean of the two middle values when the
    count is even, and `0.0` for an empty class.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
import pysam
from statistics import median

counts = {"FR": [], "RF": [], "TANDEM": []}
bam = pysam.AlignmentFile("/app/data/pairs.bam", "rb")
for a in bam:
    f = a.flag
    if not (f & 0x1) or not (f & 0x2):
        continue
    if not (f & 0x40):
        continue
    if f & (0x100 | 0x800 | 0x400):
        continue
    if (f & 0x4) or (f & 0x8):
        continue
    if a.reference_id != a.next_reference_id:
        continue
    rev, mrev = bool(f & 0x10), bool(f & 0x20)
    if rev == mrev:
        counts["TANDEM"].append(abs(a.template_length))
        continue
    if a.reference_start <= a.next_reference_start:
        left_rev = rev
    else:
        left_rev = mrev
    counts["RF" if left_rev else "FR"].append(abs(a.template_length))

with open("/app/output/pair_orientation.tsv", "w") as fh:
    fh.write("orientation\tn_pairs\tmedian_abs_tlen\n")
    for o in ("FR", "RF", "TANDEM"):
        v = counts[o]
        fh.write(f"{o}\t{len(v)}\t{median(v):.1f}\n" if v else f"{o}\t0\t0.0\n")
PY
"""
    write_task(name, "alignment", ["bam", "flags", "orientation", "insert-size"],
               instruction, expected, solve, "/app/output/pair_orientation.tsv",
               tol=0.05)
    print(f"  {name}: " + " ".join(f"{o}={len(counted[o])}" for o in counted))


# ------------------------------------------------------- 2. UTR lengths
def gen_utr_lengths(root: Path) -> None:
    name = "gtf-utr-lengths"
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(770424)

    gtf, rows = [], []
    pos = 5_000
    for gi in range(1, 19):
        gene = f"GENE{gi:03d}"
        strand = "+" if gi % 2 else "-"
        n_exons = rng.randrange(3, 6)
        exons = []
        p = pos
        for _ in range(n_exons):
            ln = rng.randrange(90, 400)
            exons.append((p, p + ln - 1))
            p += ln + rng.randrange(200, 900)
        pos = p + 3000
        tx = f"{gene}.1"
        gtf.append((exons[0][0], exons[-1][1], "gene", gene, tx, strand))
        gtf.append((exons[0][0], exons[-1][1], "transcript", gene, tx, strand))
        for s, e in exons:
            gtf.append((s, e, "exon", gene, tx, strand))

        # Every third transcript is non-coding and must be omitted entirely.
        if gi % 3 == 0:
            continue

        flat = [(s, e) for s, e in exons]
        exonic = sum(e - s + 1 for s, e in flat)
        # CDS starts inside the second exon and ends inside the penultimate one.
        cds_start = flat[1][0] + rng.randrange(10, 60)
        cds_end = flat[-2][1] - rng.randrange(10, 60)
        cds_parts = []
        for s, e in flat:
            cs, ce = max(s, cds_start), min(e, cds_end)
            if cs <= ce:
                cds_parts.append((cs, ce))
        for s, e in cds_parts:
            gtf.append((s, e, "CDS", gene, tx, strand))

        cds_len = sum(e - s + 1 for s, e in cds_parts)
        up = sum(max(0, min(e, cds_start - 1) - s + 1) for s, e in flat)
        down = sum(max(0, e - max(s, cds_end + 1) + 1) for s, e in flat)
        assert up + down + cds_len == exonic, (up, down, cds_len, exonic)
        utr5, utr3 = (up, down) if strand == "+" else (down, up)
        rows.append((tx, gene, strand, utr5, utr3, cds_len))

    gtf.sort(key=lambda r: (r[0], {"gene": 0, "transcript": 1, "exon": 2, "CDS": 3}[r[2]]))
    with (d / "annotation.gtf").open("w") as fh:
        for s, e, feat, gene, tx, strand in gtf:
            attrs = f'gene_id "{gene}"; transcript_id "{tx}";'
            frame = "0" if feat == "CDS" else "."
            fh.write(f"chr1\ttest\t{feat}\t{s}\t{e}\t.\t{strand}\t{frame}\t{attrs}\n")

    rows.sort(key=lambda r: r[0])
    lines = ["tx_id\tgene_id\tstrand\tutr5_len\tutr3_len\tcds_len"]
    lines += ["\t".join(map(str, r)) for r in rows]
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/annotation.gtf` has `gene`, `transcript`, `exon` and `CDS`
    records on both strands. Every transcript has exons; only some have CDS.

    For each transcript with at least one `CDS` record, reconstruct its
    untranslated regions from the exon and CDS coordinates.

    Let `cds_start` be that transcript's smallest CDS start and `cds_end` its
    largest CDS end (GTF coordinates are 1-based inclusive). Exonic bases
    strictly before `cds_start` form one UTR; exonic bases strictly after
    `cds_end` form the other. On a `+` transcript the upstream side is the
    5' UTR; on a `-` transcript it is the 3' UTR. `cds_len` is the total length
    of the transcript's CDS records.

    Only exonic bases count -- intronic gaps belong to no UTR.

    Write `/app/output/utr_lengths.tsv` with header

    `tx_id	gene_id	strand	utr5_len	utr3_len	cds_len`

    one row per coding transcript, sorted by `tx_id`. Transcripts without CDS
    must not appear.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
import re
from collections import defaultdict

exons = defaultdict(list)
cds = defaultdict(list)
meta = {}
for line in open("/app/data/annotation.gtf"):
    if line.startswith("#"):
        continue
    f = line.rstrip("\n").split("\t")
    if len(f) < 9:
        continue
    feat, s, e, strand, attrs = f[2], int(f[3]), int(f[4]), f[6], f[8]
    tx = re.search(r'transcript_id "([^"]+)"', attrs)
    gene = re.search(r'gene_id "([^"]+)"', attrs)
    if not tx:
        continue
    tx = tx.group(1)
    if feat == "exon":
        exons[tx].append((s, e))
        meta[tx] = (gene.group(1) if gene else "", strand)
    elif feat == "CDS":
        cds[tx].append((s, e))
        meta[tx] = (gene.group(1) if gene else "", strand)

rows = []
for tx, parts in cds.items():
    cs, ce = min(p[0] for p in parts), max(p[1] for p in parts)
    ex = exons.get(tx, [])
    up = sum(max(0, min(e, cs - 1) - s + 1) for s, e in ex)
    down = sum(max(0, e - max(s, ce + 1) + 1) for s, e in ex)
    cds_len = sum(e - s + 1 for s, e in parts)
    gene, strand = meta[tx]
    utr5, utr3 = (up, down) if strand == "+" else (down, up)
    rows.append((tx, gene, strand, utr5, utr3, cds_len))

rows.sort(key=lambda r: r[0])
with open("/app/output/utr_lengths.tsv", "w") as fh:
    fh.write("tx_id\tgene_id\tstrand\tutr5_len\tutr3_len\tcds_len\n")
    for r in rows:
        fh.write("\t".join(map(str, r)) + "\n")
PY
"""
    write_task(name, "metadata", ["gtf", "utr", "cds", "strand"],
               instruction, expected, solve, "/app/output/utr_lengths.tsv")
    print(f"  {name}: {len(rows)} coding transcripts")


# --------------------------------------------------- 3. strict de novo calls
def gen_denovo(root: Path) -> None:
    name = "vcf-denovo-strict"
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(31415)

    header = [
        "##fileformat=VCFv4.2",
        '##FILTER=<ID=PASS,Description="All filters passed">',
        '##FILTER=<ID=LowQual,Description="Low quality">',
        '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
        '##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">',
        '##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Depth">',
        "##contig=<ID=chr1,length=2000000>",
        "##contig=<ID=chr2,length=2000000>",
        "##contig=<ID=chrX,length=1500000>",
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tCHILD\tFATHER\tMOTHER",
    ]

    def sample(gt, dp, alt_frac):
        alt = int(round(dp * alt_frac))
        return f"{gt}:{dp - alt},{alt}:{dp}"

    body, rows = [], []
    pos = {"chr1": 10_000, "chr2": 12_000, "chrX": 9_000}
    for i in range(150):
        chrom = rng.choice(["chr1", "chr1", "chr2", "chrX"])
        pos[chrom] += rng.randrange(300, 2500)
        p = pos[chrom]
        ref, alt = rng.choice([("A", "G"), ("C", "T"), ("G", "A"), ("T", "C")])
        kind = rng.random()
        filt = "PASS" if rng.random() < 0.85 else "LowQual"

        if kind < 0.28:                      # candidate de novo pattern
            dp_c = rng.choice([8, 9, 12, 18, 25, 30, 40])
            ab = rng.choice([0.12, 0.2, 0.3, 0.45, 0.5, 0.55, 0.8])
            dp_f = rng.choice([7, 11, 20, 28])
            dp_m = rng.choice([6, 13, 22, 31])
            f_alt = 0 if rng.random() < 0.75 else 1
            m_alt = 0 if rng.random() < 0.8 else 1
            child = sample("0/1", dp_c, ab)
            father = f"0/0:{dp_f - f_alt},{f_alt}:{dp_f}"
            mother = f"0/0:{dp_m - m_alt},{m_alt}:{dp_m}"
            multi = False
        elif kind < 0.45:                    # inherited
            child, father, mother = (sample("0/1", 30, 0.5),
                                     sample("0/1", 30, 0.5),
                                     sample("0/0", 30, 0.0))
            multi = False
        elif kind < 0.55:                    # multiallelic decoy
            alt = "G,T"
            child, father, mother = ("0/1:10,5,3:18", "0/0:20,0,0:20", "0/0:19,0,0:19")
            multi = True
        else:                                # hom ref / hom alt / missing
            child = rng.choice([sample("0/0", 25, 0.0), sample("1/1", 25, 1.0), "./.:.,.:."])
            father, mother = sample("0/0", 25, 0.0), sample("0/0", 25, 0.0)
            multi = False

        body.append(f"{chrom}\t{p}\t.\t{ref}\t{alt}\t50\t{filt}\t.\tGT:AD:DP\t{child}\t{father}\t{mother}")

        # Reference classification.
        if multi or chrom == "chrX" or filt not in ("PASS", "."):
            continue
        cf = child.split(":")
        if cf[0] not in ("0/1", "1/0"):
            continue
        if father.split(":")[0] != "0/0" or mother.split(":")[0] != "0/0":
            continue
        try:
            c_ref, c_alt = (int(x) for x in cf[1].split(","))
            dpc = int(cf[2]); dpf = int(father.split(":")[2]); dpm = int(mother.split(":")[2])
            f_alt = int(father.split(":")[1].split(",")[1])
            m_alt = int(mother.split(":")[1].split(",")[1])
        except ValueError:
            continue
        ab = c_alt / (c_ref + c_alt) if (c_ref + c_alt) else 0.0
        ok = (dpc >= 10 and dpf >= 10 and dpm >= 10
              and 0.25 <= ab <= 0.75 and f_alt == 0 and m_alt == 0)
        rows.append((chrom, p, ref, alt, "denovo" if ok else "uncertain", f"{ab:.4f}"))

    # tabix needs a coordinate-sorted file, and chromosomes are drawn at random
    # above, so sort the body before writing.
    contig_order = {"chr1": 0, "chr2": 1, "chrX": 2}
    body.sort(key=lambda ln: (contig_order[ln.split("\t")[0]], int(ln.split("\t")[1])))

    vcf = d / "trio.vcf"
    vcf.write_text("\n".join(header + body) + "\n")
    subprocess.run(["bgzip", "-f", str(vcf)], check=True)
    subprocess.run(["tabix", "-p", "vcf", str(vcf) + ".gz"], check=True)

    order = {"chr1": 0, "chr2": 1, "chrX": 2}
    rows.sort(key=lambda r: (order[r[0]], r[1]))
    lines = ["chrom\tpos\tref\talt\tclass\tchild_ab"]
    lines += ["\t".join(map(str, r)) for r in rows]
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/trio.vcf.gz` (with `.tbi`) holds samples `CHILD`, `FATHER`,
    `MOTHER` with `FORMAT` `GT:AD:DP`.

    Find candidate *de novo* variants in the child and say which are supported.

    Use only biallelic SNVs (single-base REF, one single-base ALT) on an
    autosome (`chrX` excluded) with `FILTER` `PASS` or `.`.

    A site is a **candidate** when `CHILD` is heterozygous (`0/1` or `1/0`) and
    both parents are `0/0`. Report every candidate, classified as:

    - `denovo` when all hold: `DP` at least 10 in all three samples; child
      allele balance between 0.25 and 0.75 inclusive; and ALT allelic depth
      exactly 0 in both parents;
    - `uncertain` when it is a candidate but any of those fails.

    Child allele balance is `AD_alt / (AD_ref + AD_alt)`.

    Write `/app/output/denovo.tsv` with header

    `chrom	pos	ref	alt	class	child_ab`

    one row per candidate, `child_ab` to four decimals, sorted by chromosome
    (`chr1` before `chr2`) then ascending position.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
import gzip

order = {"chr1": 0, "chr2": 1}
rows = []
with gzip.open("/app/data/trio.vcf.gz", "rt") as fh:
    for line in fh:
        if line.startswith("#"):
            continue
        f = line.rstrip("\n").split("\t")
        chrom, pos, ref, alt, filt = f[0], int(f[1]), f[3], f[4], f[6]
        if chrom not in order:
            continue
        if filt not in ("PASS", "."):
            continue
        if len(ref) != 1 or "," in alt or len(alt) != 1:
            continue
        keys = f[8].split(":")
        child, father, mother = (dict(zip(keys, s.split(":"))) for s in f[9:12])
        if child.get("GT") not in ("0/1", "1/0"):
            continue
        if father.get("GT") != "0/0" or mother.get("GT") != "0/0":
            continue
        try:
            c_ref, c_alt = (int(x) for x in child["AD"].split(","))
            dpc, dpf, dpm = int(child["DP"]), int(father["DP"]), int(mother["DP"])
            f_alt = int(father["AD"].split(",")[1])
            m_alt = int(mother["AD"].split(",")[1])
        except (ValueError, KeyError):
            continue
        ab = c_alt / (c_ref + c_alt) if (c_ref + c_alt) else 0.0
        ok = (dpc >= 10 and dpf >= 10 and dpm >= 10
              and 0.25 <= ab <= 0.75 and f_alt == 0 and m_alt == 0)
        rows.append((chrom, pos, ref, alt, "denovo" if ok else "uncertain", f"{ab:.4f}"))

rows.sort(key=lambda r: (order[r[0]], r[1]))
with open("/app/output/denovo.tsv", "w") as fh:
    fh.write("chrom\tpos\tref\talt\tclass\tchild_ab\n")
    for r in rows:
        fh.write("\t".join(map(str, r)) + "\n")
PY
"""
    write_task(name, "variant", ["vcf", "trio", "denovo", "filters"],
               instruction, expected, solve, "/app/output/denovo.tsv", tol=5e-5)
    n_dn = sum(1 for r in rows if r[4] == "denovo")
    print(f"  {name}: {len(rows)} candidates ({n_dn} denovo, {len(rows) - n_dn} uncertain)")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    gen_pair_orientation(root)
    gen_utr_lengths(root)
    gen_denovo(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
