#!/usr/bin/env python3
"""Generate v1.0 hard candidates, batch 6 -- long exacting outputs.

Five batches in, the pattern is clear: the strongest e-INFRA model solves 18 of
the 19 new tasks on every attempt, and the single trial it lost was on
`hmm-viterbi-segments`, the task with the longest computed output. Neither
algorithmic depth nor scale separated it. What did, once, was *length* -- many
rows, each of which must be exactly right.

So these two are deliberately long and unforgiving. Both are ordinary
bioinformatics that a careful human does correctly and slowly:

* `gtf-cds-integrity` checks 250 transcripts for start codon, stop codon,
  frame and internal stops, which needs strand, CDS phase, reverse complement
  and the genetic code all handled together.
* `vcf-leftalign-concordance` left-aligns indels in two call sets and compares
  them, the normalisation step that silently breaks most naive comparisons.

    docker run --rm -v "$PWD":/repo -w /repo bioterm-base:v1 \
        python3 scripts/generate_hard_candidates_batch6.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hard_candidate_common import write_task  # noqa: E402

CODON_STOP = {"TAA", "TAG", "TGA"}
COMP = str.maketrans("ACGT", "TGCA")


def rc(s: str) -> str:
    return s.translate(COMP)[::-1]


# ------------------------------------------------------- 20. CDS integrity
def gen_cds_integrity(root: Path) -> None:
    name = "gtf-cds-integrity"
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(778811)

    contigs = {"ctg1": [], "ctg2": []}
    for c in contigs:
        contigs[c] = [rng.choice("ACGT") for _ in range(400_000)]

    gtf_rows = []
    transcripts = []
    cursor = {"ctg1": 1000, "ctg2": 1000}

    def place(chrom: str, strand: str, n_exons: int, kind: str) -> None:
        """Write one transcript's CDS into the contig and record it."""
        seq = contigs[chrom]
        start = cursor[chrom]
        pieces, blocks = [], []
        for _ in range(n_exons):
            ln = rng.randrange(2, 7) * 3
            blocks.append((start, start + ln - 1))
            pieces.append(ln)
            start += ln + rng.randrange(80, 400)
        cursor[chrom] = start + rng.randrange(500, 2000)

        total = sum(pieces)
        n_codons = total // 3
        codons = []
        for i in range(n_codons):
            if i == 0:
                codons.append("ATG" if kind != "no_start" else rng.choice(["CTG", "GTG", "TTG"]))
            elif i == n_codons - 1:
                codons.append("TAA" if kind != "no_stop" else "CAA")
            else:
                codons.append(rng.choice([c for c in
                                          ["GCT", "CGT", "AAT", "GAT", "TGT", "CAA", "GGT",
                                           "CAT", "ATT", "TTA", "AAA", "ATG", "TTT", "CCT",
                                           "TCT", "ACT", "TGG", "TAT", "GTT"]]))
        if kind == "internal_stop":
            pos = rng.randrange(1, max(2, n_codons - 1))
            codons[pos] = rng.choice(sorted(CODON_STOP))
        cds = "".join(codons)
        if kind == "frameshift":
            cds = cds[:-1]                       # length no longer a multiple of 3
            blocks[-1] = (blocks[-1][0], blocks[-1][1] - 1)

        written = cds if strand == "+" else rc(cds)
        off = 0
        for s, e in blocks:
            ln = e - s + 1
            seq[s - 1:s - 1 + ln] = list(written[off:off + ln])
            off += ln

        tx = f"TX{len(transcripts) + 1:04d}"
        gene = f"G{len(transcripts) + 1:04d}"
        lo, hi = blocks[0][0], blocks[-1][1]
        gtf_rows.append((chrom, "gene", lo, hi, strand, f'gene_id "{gene}";'))
        gtf_rows.append((chrom, "transcript", lo, hi, strand,
                         f'gene_id "{gene}"; transcript_id "{tx}";'))
        ordered = blocks if strand == "+" else blocks[::-1]
        phase = 0
        for s, e in ordered:
            gtf_rows.append((chrom, "exon", s, e, strand,
                             f'gene_id "{gene}"; transcript_id "{tx}";'))
        for s, e in ordered:
            gtf_rows.append((chrom, "CDS", s, e, strand,
                             f'gene_id "{gene}"; transcript_id "{tx}";', phase))
            phase = (3 - ((e - s + 1) - phase) % 3) % 3
        transcripts.append((tx, gene, chrom, strand, blocks))

    kinds = (["ok"] * 150 + ["no_start"] * 25 + ["no_stop"] * 25
             + ["internal_stop"] * 30 + ["frameshift"] * 20)
    rng.shuffle(kinds)
    for kind in kinds:
        place(rng.choice(["ctg1", "ctg2"]), rng.choice(["+", "-"]),
              rng.randrange(1, 4), kind)

    with (d / "genome.fa").open("w") as fh:
        for c, seq in contigs.items():
            s = "".join(seq)
            fh.write(f">{c}\n")
            for i in range(0, len(s), 60):
                fh.write(s[i:i + 60] + "\n")

    with (d / "annotation.gtf").open("w") as fh:
        for row in sorted(gtf_rows, key=lambda r: (r[0], r[2], r[1])):
            chrom, feat, s, e, strand, attrs = row[:6]
            frame = str(row[6]) if len(row) > 6 else "."
            fh.write(f"{chrom}\tsrc\t{feat}\t{s}\t{e}\t.\t{strand}\t{frame}\t{attrs}\n")

    genome = {c: "".join(seq) for c, seq in contigs.items()}
    rows = []
    for tx, _gene, chrom, strand, blocks in transcripts:
        ordered = sorted(blocks) if strand == "+" else sorted(blocks, reverse=True)
        parts = []
        for s, e in ordered:
            piece = genome[chrom][s - 1:e]
            parts.append(piece if strand == "+" else rc(piece))
        cds = "".join(parts)
        n = len(cds)
        in_frame = n % 3 == 0
        codons = [cds[i:i + 3] for i in range(0, n - n % 3, 3)]
        has_start = codons[0] == "ATG" if codons else False
        has_stop = codons[-1] in CODON_STOP if codons else False
        internal = sum(1 for c in codons[:-1] if c in CODON_STOP)
        if not in_frame:
            status = "not_multiple_of_three"
        elif not has_start:
            status = "no_start_codon"
        elif internal:
            status = "internal_stop"
        elif not has_stop:
            status = "no_stop_codon"
        else:
            status = "ok"
        rows.append((tx, chrom, strand, n,
                     "yes" if has_start else "no",
                     "yes" if has_stop else "no", internal, status))

    rows.sort(key=lambda r: r[0])
    lines = ["tx_id\tchrom\tstrand\tcds_len\thas_start\thas_stop\tn_internal_stops\tstatus"]
    lines += ["\t".join(map(str, r)) for r in rows]
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/annotation.gtf` annotates `/app/data/genome.fa`. Every
    transcript has `exon` and `CDS` records.

    Check each transcript's coding sequence and report what is wrong with it.

    Build a transcript's CDS by taking its `CDS` records, ordering them along
    the direction of transcription, extracting each from the genome, and
    reverse-complementing every piece on a `-` strand transcript before
    concatenating. GTF coordinates are 1-based inclusive.

    Read codons from the start of that sequence. Then decide `status` by the
    **first** of these that applies, in this order:

    1. `not_multiple_of_three` -- the CDS length is not divisible by 3;
    2. `no_start_codon` -- the first codon is not `ATG`;
    3. `internal_stop` -- a stop codon (`TAA`, `TAG`, `TGA`) occurs anywhere
       before the final codon;
    4. `no_stop_codon` -- the final codon is not a stop codon;
    5. `ok`.

    Write `/app/output/cds_report.tsv` with header

    `tx_id\tchrom\tstrand\tcds_len\thas_start\thas_stop\tn_internal_stops\tstatus`

    one row per transcript sorted by `tx_id`, with `has_start` and `has_stop`
    as `yes` or `no` and `n_internal_stops` counting stop codons before the
    final codon.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
import re
from collections import defaultdict

COMP = str.maketrans("ACGT", "TGCA")
STOP = {"TAA", "TAG", "TGA"}


def rc(s):
    return s.translate(COMP)[::-1]


genome, name, buf = {}, None, []
for line in open("/app/data/genome.fa"):
    if line.startswith(">"):
        if name:
            genome[name] = "".join(buf)
        name, buf = line[1:].strip().split()[0], []
    else:
        buf.append(line.strip())
if name:
    genome[name] = "".join(buf)

cds = defaultdict(list)
info = {}
for line in open("/app/data/annotation.gtf"):
    if line.startswith("#"):
        continue
    f = line.rstrip("\n").split("\t")
    if f[2] != "CDS":
        continue
    m = re.search(r'transcript_id "([^"]+)"', f[8])
    tx = m.group(1)
    cds[tx].append((int(f[3]), int(f[4])))
    info[tx] = (f[0], f[6])

rows = []
for tx, blocks in cds.items():
    chrom, strand = info[tx]
    ordered = sorted(blocks) if strand == "+" else sorted(blocks, reverse=True)
    parts = []
    for s, e in ordered:
        piece = genome[chrom][s - 1:e]
        parts.append(piece if strand == "+" else rc(piece))
    seq = "".join(parts)
    n = len(seq)
    codons = [seq[i:i + 3] for i in range(0, n - n % 3, 3)]
    has_start = bool(codons) and codons[0] == "ATG"
    has_stop = bool(codons) and codons[-1] in STOP
    internal = sum(1 for c in codons[:-1] if c in STOP)
    if n % 3:
        status = "not_multiple_of_three"
    elif not has_start:
        status = "no_start_codon"
    elif internal:
        status = "internal_stop"
    elif not has_stop:
        status = "no_stop_codon"
    else:
        status = "ok"
    rows.append((tx, chrom, strand, n, "yes" if has_start else "no",
                 "yes" if has_stop else "no", internal, status))

rows.sort(key=lambda r: r[0])
with open("/app/output/cds_report.tsv", "w") as fh:
    fh.write("tx_id\tchrom\tstrand\tcds_len\thas_start\thas_stop\t"
             "n_internal_stops\tstatus\n")
    for r in rows:
        fh.write("\t".join(map(str, r)) + "\n")
PY
"""
    write_task(name, "metadata", ["gtf", "cds", "genetic-code", "strand"],
               instruction, expected, solve, "/app/output/cds_report.tsv")
    from collections import Counter
    print(f"  {name}: {len(rows)} transcripts, {dict(Counter(r[7] for r in rows))}")


# --------------------------------------------- 21. left-align + concordance
def gen_leftalign(root: Path) -> None:
    name = "vcf-leftalign-concordance"
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(9182736)

    ref = "".join(rng.choice("ACGT") for _ in range(60_000))
    # Homopolymers and short tandem repeats are where left-alignment matters.
    ref_list = list(ref)
    for _ in range(400):
        p = rng.randrange(100, 59_000)
        unit = rng.choice(["A", "T", "AT", "AC", "GAA", "CT"])
        for i in range(rng.randrange(6, 18)):
            for j, ch in enumerate(unit):
                if p + i * len(unit) + j < len(ref_list):
                    ref_list[p + i * len(unit) + j] = ch
    ref = "".join(ref_list)
    with (d / "reference.fa").open("w") as fh:
        fh.write(">chr1\n")
        for i in range(0, len(ref), 60):
            fh.write(ref[i:i + 60] + "\n")

    def normalise(pos: int, r: str, a: str) -> tuple[int, str, str]:
        """vt-style left-alignment, then parsimony trimming.

        The trailing-base trim must fire when only ONE allele is longer than a
        single base -- that is the step that rolls an indel leftwards through a
        repeat. Guarding it with `len(r) > 1 and len(a) > 1` disables
        normalisation entirely, which is what an earlier version did.
        """
        while True:
            if len(r) == 0 or len(a) == 0:
                pos -= 1
                b = ref[pos - 1]
                r, a = b + r, b + a
                continue
            if r[-1] == a[-1] and (len(r) > 1 or len(a) > 1):
                r, a = r[:-1], a[:-1]
                continue
            break
        while len(r) > 1 and len(a) > 1 and r[0] == a[0]:
            pos += 1
            r, a = r[1:], a[1:]
        return pos, r, a

    def make_variant() -> tuple[int, str, str]:
        p = rng.randrange(200, 59_000)
        kind = rng.random()
        if kind < 0.4:                                   # SNV
            r = ref[p - 1]
            a = rng.choice([b for b in "ACGT" if b != r])
            return p, r, a
        if kind < 0.7:                                   # deletion
            ln = rng.randrange(1, 6)
            return p, ref[p - 1:p - 1 + ln + 1], ref[p - 1]
        ln = rng.randrange(1, 6)                         # insertion
        return p, ref[p - 1], ref[p - 1] + "".join(rng.choice("ACGT") for _ in range(ln))

    shared = [make_variant() for _ in range(120)]
    only_a = [make_variant() for _ in range(40)]
    only_b = [make_variant() for _ in range(40)]

    def shift_right(pos: int, r: str, a: str) -> tuple[int, str, str]:
        """Re-express the same event further right, where possible."""
        for _ in range(rng.randrange(1, 4)):
            nxt = ref[pos - 1 + len(r)] if pos - 1 + len(r) < len(ref) else None
            if nxt is None or len(r) == len(a):
                break
            r2, a2 = r + nxt, a + nxt
            if r2[0] == a2[0] and len(r2) > 1 and len(a2) > 1:
                pos, r, a = pos + 1, r2[1:], a2[1:]
            else:
                break
        return pos, r, a

    def write_vcf(path: Path, variants, jitter: bool) -> None:
        rows = []
        for p, r, a in variants:
            rows.append(shift_right(p, r, a) if jitter else (p, r, a))
        rows.sort(key=lambda t: t[0])
        with path.open("w") as fh:
            fh.write("##fileformat=VCFv4.2\n##contig=<ID=chr1,length=60000>\n")
            fh.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
            for p, r, a in rows:
                fh.write(f"chr1\t{p}\t.\t{r}\t{a}\t60\tPASS\t.\n")

    write_vcf(d / "callset_a.vcf", shared + only_a, False)
    write_vcf(d / "callset_b.vcf", shared + only_b, True)

    def keyset(variants):
        return {normalise(p, r, a) for p, r, a in variants}

    def read_vcf(path: Path):
        out = []
        for line in path.read_text().splitlines():
            if line.startswith("#"):
                continue
            f = line.split("\t")
            out.append((int(f[1]), f[3], f[4]))
        return out

    a_keys = keyset(read_vcf(d / "callset_a.vcf"))
    b_keys = keyset(read_vcf(d / "callset_b.vcf"))
    rows = []
    for k in sorted(a_keys | b_keys):
        label = ("shared" if k in a_keys and k in b_keys
                 else "only_a" if k in a_keys else "only_b")
        rows.append((k[0], k[1], k[2], label))
    lines = ["pos\tref\talt\tstatus"]
    lines += ["\t".join(map(str, r)) for r in rows]
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/callset_a.vcf` and `/app/data/callset_b.vcf` call the same
    sample against `/app/data/reference.fa`. Many indels sit in repeats and are
    written at different positions in the two files, so they must be normalised
    before they can be compared.

    Left-align and trim every variant in both files, then compare.

    Normalise one variant by repeating these two steps until neither applies:

    1. if REF or ALT is empty, move the position one base left and prepend that
       reference base to both;
    2. otherwise, if REF and ALT end with the same base and at least one of
       them is longer than a single base, drop that last base from both.

    Then, while REF and ALT are both longer than one base and start with the
    same base, drop that first base from both and move the position one right.

    Two variants are the same when their normalised position, REF and ALT all
    match.

    Write `/app/output/concordance.tsv` with header

    `pos\tref\talt\tstatus`

    one row per distinct normalised variant across both files, sorted by
    position then REF then ALT, with `status` being `shared`, `only_a` or
    `only_b`.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
ref, buf = None, []
for line in open("/app/data/reference.fa"):
    if line.startswith(">"):
        continue
    buf.append(line.strip())
ref = "".join(buf)


def normalise(pos, r, a):
    while True:
        if len(r) == 0 or len(a) == 0:
            pos -= 1
            b = ref[pos - 1]
            r, a = b + r, b + a
            continue
        if r[-1] == a[-1] and (len(r) > 1 or len(a) > 1):
            r, a = r[:-1], a[:-1]
            continue
        break
    while len(r) > 1 and len(a) > 1 and r[0] == a[0]:
        pos += 1
        r, a = r[1:], a[1:]
    return pos, r, a


def load(path):
    out = set()
    for line in open(path):
        if line.startswith("#"):
            continue
        f = line.rstrip("\n").split("\t")
        out.add(normalise(int(f[1]), f[3], f[4]))
    return out


A = load("/app/data/callset_a.vcf")
B = load("/app/data/callset_b.vcf")

with open("/app/output/concordance.tsv", "w") as fh:
    fh.write("pos\tref\talt\tstatus\n")
    for k in sorted(A | B):
        st = "shared" if k in A and k in B else ("only_a" if k in A else "only_b")
        fh.write(f"{k[0]}\t{k[1]}\t{k[2]}\t{st}\n")
PY
"""
    write_task(name, "variant", ["vcf", "normalisation", "left-align", "concordance"],
               instruction, expected, solve, "/app/output/concordance.tsv")
    from collections import Counter
    print(f"  {name}: {len(rows)} variants, {dict(Counter(r[3] for r in rows))}")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    gen_cds_integrity(root)
    gen_leftalign(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
