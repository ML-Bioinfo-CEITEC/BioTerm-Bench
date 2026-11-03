#!/usr/bin/env python3
"""Generate v1.0 hard candidates, batch 7 -- plausible-wrong-answer traps.

Six batches of hypotheses about difficulty were mostly wrong. More rules,
deeper algorithms, larger inputs, more deliverables and longer outputs all
failed to trouble the strongest model. Reading the actual grader diagnoses
showed what did work:

    vcf-leftalign-concordance   expected 200 data rows, got 274
    counts-fisher-bh-fdr        expected 157 data rows, got 400

Both failures are *confident wrong answers*: the number you get from a
reasonable-looking shortcut. That, not complexity, is what separates models.

Each task here is fully specified -- nothing is hidden or ambiguous -- but each
has a shortcut that a competent-looking implementation reaches for and that
returns a plausible wrong result:

* summing exon lengths instead of merging overlapping exons;
* averaging Phred scores instead of averaging error probabilities;
* dividing by library size before length instead of after.

    docker run --rm -v "$PWD":/repo -w /repo bioterm-base:v1 \
        python3 scripts/generate_hard_candidates_batch7.py
"""

from __future__ import annotations

import math
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hard_candidate_common import write_task  # noqa: E402

#: The sentences that name each pitfall out loud, exactly as they appear in
#: the instruction source. Batch 7 shipped with them and every model scored
#: 6/6, which leaves the trap untested rather than absent: a warned-about
#: pitfall is a specification, not a trap. The -nohint variants delete these
#: verbatim, leaving every column definition intact, so the task stays fully
#: specified and only the nudge is gone. Deleting a substring keeps the
#: surrounding indentation exactly as textwrap.dedent expects it.
HINT_GTF = """    These are not the same number, and only `merged_exon_len` is the gene's
    real exonic footprint.

"""
HINT_FASTQ = """    Averaging Phred scores and converting that average back to a probability is
    not the same thing as averaging the probabilities, because the conversion
    is not linear. `mean_q` and `equivalent_q` will differ, and both are asked
    for.

"""
HINT_TPM = """    The two differ only in the order of the two normalisations, and that order
    matters.

"""




# ------------------------------------------- 22. merged vs summed exon length
def gen_exonic_length(root: Path, suffix: str = "", seed: int = 515151,
                      hint: bool = True) -> None:
    name = "gtf-merged-exonic-length" + suffix
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    rows, genes = [], []
    cursor = 1000
    for g in range(1, 121):
        gene = f"GENE{g:04d}"
        n_tx = rng.randrange(1, 5)
        gene_start = cursor
        exons_by_tx = []
        for t in range(n_tx):
            pos = gene_start + rng.randrange(0, 400)
            exons = []
            for _ in range(rng.randrange(2, 7)):
                ln = rng.randrange(60, 400)
                exons.append((pos, pos + ln - 1))
                pos += ln + rng.randrange(100, 900)
            exons_by_tx.append(exons)
        gene_end = max(e for tx in exons_by_tx for _s, e in tx)
        strand = rng.choice("+-")
        rows.append((gene, "gene", gene_start, gene_end, strand, gene, None))
        for t, exons in enumerate(exons_by_tx, start=1):
            tx = f"{gene}.{t}"
            rows.append((gene, "transcript", min(s for s, _ in exons),
                         max(e for _, e in exons), strand, gene, tx))
            for s, e in exons:
                rows.append((gene, "exon", s, e, strand, gene, tx))
        genes.append((gene, strand, gene_start, gene_end, exons_by_tx))
        cursor = gene_end + rng.randrange(2000, 6000)

    with (d / "annotation.gtf").open("w") as fh:
        for _g, feat, s, e, strand, gene, tx in rows:
            attrs = f'gene_id "{gene}";'
            if tx:
                attrs += f' transcript_id "{tx}";'
            fh.write(f"chr1\tsrc\t{feat}\t{s}\t{e}\t.\t{strand}\t.\t{attrs}\n")

    def merge(intervals):
        out = []
        for s, e in sorted(intervals):
            if out and s <= out[-1][1] + 1:
                out[-1][1] = max(out[-1][1], e)
            else:
                out.append([s, e])
        return out

    lines = ["gene_id\tn_transcripts\tsummed_exon_len\tmerged_exon_len\tintronic_len"]
    for gene, _strand, gs, ge, exons_by_tx in genes:
        flat = [x for tx in exons_by_tx for x in tx]
        summed = sum(e - s + 1 for s, e in flat)
        merged = sum(e - s + 1 for s, e in merge(flat))
        lines.append(f"{gene}\t{len(exons_by_tx)}\t{summed}\t{merged}\t"
                     f"{(ge - gs + 1) - merged}")
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/annotation.gtf` has `gene`, `transcript` and `exon` records on
    one contig. A gene may have several transcripts, and their exons often
    overlap each other.

    For each gene report both the naive and the correct exonic length.

    GTF coordinates are 1-based and inclusive, so an exon covers
    `end - start + 1` bases.

    - `summed_exon_len` adds up the lengths of **every** exon record of the
      gene, counting shared bases once per transcript that contains them.
    - `merged_exon_len` counts each genomic base **once**: take the union of
      all the gene's exon intervals and total its length. Two intervals that
      touch or overlap -- that is, where the next start is no more than one
      past the previous end -- belong to the same merged block.
    - `intronic_len` is the gene record's own length minus `merged_exon_len`.

    These are not the same number, and only `merged_exon_len` is the gene's
    real exonic footprint.

    Write `/app/output/exonic_lengths.tsv` with header

    `gene_id\tn_transcripts\tsummed_exon_len\tmerged_exon_len\tintronic_len`

    one row per gene sorted by `gene_id`.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
import re
from collections import defaultdict

exons = defaultdict(list)
tx_of = defaultdict(set)
gene_span = {}
for line in open("/app/data/annotation.gtf"):
    if line.startswith("#"):
        continue
    f = line.rstrip("\n").split("\t")
    gene = re.search(r'gene_id "([^"]+)"', f[8]).group(1)
    s, e = int(f[3]), int(f[4])
    if f[2] == "gene":
        gene_span[gene] = (s, e)
    elif f[2] == "exon":
        exons[gene].append((s, e))
        tx_of[gene].add(re.search(r'transcript_id "([^"]+)"', f[8]).group(1))


def merge(intervals):
    out = []
    for s, e in sorted(intervals):
        if out and s <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


with open("/app/output/exonic_lengths.tsv", "w") as fh:
    fh.write("gene_id\tn_transcripts\tsummed_exon_len\tmerged_exon_len\tintronic_len\n")
    for gene in sorted(exons):
        flat = exons[gene]
        summed = sum(e - s + 1 for s, e in flat)
        merged = sum(e - s + 1 for s, e in merge(flat))
        gs, ge = gene_span[gene]
        fh.write(f"{gene}\t{len(tx_of[gene])}\t{summed}\t{merged}\t"
                 f"{(ge - gs + 1) - merged}\n")
PY
"""
    if not hint:
        instruction = instruction.replace(HINT_GTF, "")
    write_task(name, "metadata", ["gtf", "intervals", "merge", "exonic-length"],
               instruction, expected, solve, "/app/output/exonic_lengths.tsv")
    print(f"  {name}: {len(genes)} genes")


# ------------------------------------- 23. Phred averaging done properly
def gen_expected_errors(root: Path, suffix: str = "", seed: int = 626262,
                        hint: bool = True) -> None:
    name = "fastq-expected-errors" + suffix
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    reads = []
    for i in range(1, 2001):
        ln = rng.randrange(90, 151)
        base_q = rng.uniform(20, 38)
        quals = []
        for j in range(ln):
            # Quality decays along the read, as on a real instrument.
            q = base_q - (j / ln) * rng.uniform(2, 16) + rng.gauss(0, 2.5)
            quals.append(max(2, min(40, int(round(q)))))
        seq = "".join(rng.choice("ACGT") for _ in range(ln))
        reads.append((f"read{i:05d}", seq, quals))

    with (d / "reads.fastq").open("w") as fh:
        for rid, seq, quals in reads:
            fh.write(f"@{rid}\n{seq}\n+\n" + "".join(chr(33 + q) for q in quals) + "\n")

    rows = []
    for rid, seq, quals in reads:
        mean_q = sum(quals) / len(quals)
        errs = [10 ** (-q / 10) for q in quals]
        expected_errors = sum(errs)
        equiv = -10 * math.log10(sum(errs) / len(errs))
        if expected_errors > 1.0:
            rows.append((rid, len(seq), mean_q, expected_errors, equiv))
    rows.sort(key=lambda r: (-r[3], r[0]))
    lines = ["read_id\tlength\tmean_q\texpected_errors\tequivalent_q"]
    for rid, ln, mq, ee, eq in rows:
        lines.append(f"{rid}\t{ln}\t{mq:.4f}\t{ee:.4f}\t{eq:.4f}")
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/reads.fastq` holds 2000 reads with Phred+33 quality encoding, so
    a quality character's score is its ASCII value minus 33.

    Report the reads whose expected number of sequencing errors exceeds 1.

    A base with Phred score `Q` has error probability `P = 10 ** (-Q / 10)`.

    - `mean_q` is the plain arithmetic mean of the read's Phred scores.
    - `expected_errors` is the **sum** of the read's per-base error
      probabilities.
    - `equivalent_q` is `-10 * log10(mean_error_probability)`, where the mean
      error probability is `expected_errors` divided by the read length.

    Averaging Phred scores and converting that average back to a probability is
    not the same thing as averaging the probabilities, because the conversion
    is not linear. `mean_q` and `equivalent_q` will differ, and both are asked
    for.

    Keep only reads with `expected_errors` greater than 1.0.

    Write `/app/output/noisy_reads.tsv` with header

    `read_id\tlength\tmean_q\texpected_errors\tequivalent_q`

    sorted by descending `expected_errors` then by `read_id`, with the three
    computed columns to four decimals.
    """

    solve = r"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output
python3 - <<'PY'
import math

rows = []
with open("/app/data/reads.fastq") as fh:
    while True:
        h = fh.readline()
        if not h:
            break
        seq = fh.readline().strip()
        fh.readline()
        qual = fh.readline().strip()
        q = [ord(c) - 33 for c in qual]
        errs = [10 ** (-x / 10) for x in q]
        ee = sum(errs)
        if ee <= 1.0:
            continue
        rows.append((h[1:].strip(), len(seq), sum(q) / len(q), ee,
                     -10 * math.log10(ee / len(q))))

rows.sort(key=lambda r: (-r[3], r[0]))
with open("/app/output/noisy_reads.tsv", "w") as fh:
    fh.write("read_id\tlength\tmean_q\texpected_errors\tequivalent_q\n")
    for rid, ln, mq, ee, eq in rows:
        fh.write(f"{rid}\t{ln}\t{mq:.4f}\t{ee:.4f}\t{eq:.4f}\n")
PY
"""
    if not hint:
        instruction = instruction.replace(HINT_FASTQ, "")
    write_task(name, "qc", ["fastq", "phred", "expected-errors", "filtering"],
               instruction, expected, solve, "/app/output/noisy_reads.tsv", tol=1e-3)
    print(f"  {name}: {len(rows)} noisy reads of {len(reads)}")


# ----------------------------------------------- 24. TPM order of operations
def gen_tpm_order(root: Path, suffix: str = "", seed: int = 737373,
                  hint: bool = True) -> None:
    name = "rnaseq-tpm-rpkm-divergence" + suffix
    d = root / "tasks" / name / "data"
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    genes = [f"G{i:04d}" for i in range(1, 801)]
    samples = [f"S{i}" for i in range(1, 7)]
    lengths = {g: rng.randrange(300, 12_000) for g in genes}
    counts = {s: {g: int(rng.lognormvariate(3.0, 1.8)) for g in genes} for s in samples}

    with (d / "counts.tsv").open("w") as fh:
        fh.write("gene\tlength\t" + "\t".join(samples) + "\n")
        for g in genes:
            fh.write(f"{g}\t{lengths[g]}\t"
                     + "\t".join(str(counts[s][g]) for s in samples) + "\n")

    tpm, rpkm = {}, {}
    for s in samples:
        rates = {g: counts[s][g] / lengths[g] for g in genes}
        denom = sum(rates.values())
        tpm[s] = {g: rates[g] * 1e6 / denom for g in genes}
        total = sum(counts[s].values())
        rpkm[s] = {g: counts[s][g] * 1e9 / (lengths[g] * total) for g in genes}

    mean_tpm = {g: sum(tpm[s][g] for s in samples) / len(samples) for g in genes}
    mean_rpkm = {g: sum(rpkm[s][g] for s in samples) / len(samples) for g in genes}

    def ranks(values):
        order = sorted(genes, key=lambda g: (-values[g], g))
        return {g: i + 1 for i, g in enumerate(order)}

    rt, rr = ranks(mean_tpm), ranks(mean_rpkm)
    rows = sorted(genes, key=lambda g: (-abs(rt[g] - rr[g]), g))[:40]
    lines = ["gene\tmean_tpm\tmean_rpkm\trank_tpm\trank_rpkm\trank_shift"]
    for g in rows:
        lines.append(f"{g}\t{mean_tpm[g]:.4f}\t{mean_rpkm[g]:.4f}\t{rt[g]}\t{rr[g]}\t"
                     f"{abs(rt[g] - rr[g])}")
    expected = "\n".join(lines) + "\n"

    instruction = """
    `/app/data/counts.tsv` gives 800 genes with their length in bases and raw
    counts in six samples.

    Compute TPM and RPKM for every gene in every sample and find where the two
    measures disagree most.

    The two differ only in the order of the two normalisations, and that order
    matters.

    - **RPKM**: divide a gene's count by its length in kilobases, then by the
      sample's total count in millions.
    - **TPM**: first divide every gene's count by its length in kilobases to
      get rates, then divide each rate by the **sum of that sample's rates**
      and multiply by one million.

    For each gene take its mean TPM and mean RPKM across the six samples. Rank
    genes by descending mean TPM, and separately by descending mean RPKM, in
    both cases breaking ties by gene name ascending, with rank 1 the highest.
    `rank_shift` is the absolute difference between a gene's two ranks.

    Write `/app/output/rank_divergence.tsv` with header

    `gene\tmean_tpm\tmean_rpkm\trank_tpm\trank_rpkm\trank_shift`

    for the 40 genes with the largest `rank_shift`, sorted by descending
    `rank_shift` then by gene name, with the two means to four decimals.
    """

    solve = r"""#!/usr/bin/env bash
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
"""
    if not hint:
        instruction = instruction.replace(HINT_TPM, "")
    write_task(name, "rnaseq", ["tpm", "rpkm", "normalisation", "ranking"],
               instruction, expected, solve, "/app/output/rank_divergence.tsv", tol=1e-3)
    print(f"  {name}: max rank shift {max(abs(rt[g] - rr[g]) for g in genes)}")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    gen_exonic_length(root)
    gen_expected_errors(root)
    gen_tpm_order(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
