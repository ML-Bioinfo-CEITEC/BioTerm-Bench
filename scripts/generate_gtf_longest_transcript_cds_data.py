#!/usr/bin/env python3
"""Generate a synthetic GENCODE-style GTF + gold longest-CDS TSV.

Writes:
  /out/data/annot.gtf
  /out/gold/longest_cds.tsv

Each gene has 1-4 transcripts. Transcripts either have a CDS or not.
For every gene that has at least one CDS-bearing transcript, the gold
TSV records the transcript with max total_cds_length (tie broken by
transcript_id ASCII asc).
"""
from __future__ import annotations

import random
from pathlib import Path

SEED = 20260418
N_GENES = 40
DATA = Path("/out/data/annot.gtf")
GOLD = Path("/out/gold/longest_cds.tsv")


def attr(**kv: str) -> str:
    return "".join(f'{k} "{v}"; ' for k, v in kv.items()).rstrip()


def main() -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)
    lines: list[str] = []
    gene_to_best: dict[str, tuple[str, int, int]] = {}

    chrom = "chrSIM1"
    cursor = 1000

    for g in range(1, N_GENES + 1):
        gid = f"SIMG{g:04d}"
        n_tx = rng.randint(1, 4)
        tx_records: list[tuple[str, int, int]] = []  # tid, cds_len, n_cds

        gene_start = cursor
        for t in range(1, n_tx + 1):
            # deterministic id
            tid = f"SIMT{g:04d}.{t}"
            n_exons = rng.randint(2, 6)
            tx_start = cursor
            exon_spans: list[tuple[int, int]] = []
            for e in range(n_exons):
                exon_len = rng.randint(120, 600)
                exon_start = cursor
                exon_end = cursor + exon_len - 1
                exon_spans.append((exon_start, exon_end))
                cursor = exon_end + rng.randint(150, 800)
            tx_end = exon_spans[-1][1]

            has_cds = rng.random() < 0.8
            cds_len = 0
            n_cds = 0
            cds_spans: list[tuple[int, int]] = []
            if has_cds:
                first_cds_exon = rng.randint(0, max(0, n_exons - 2))
                last_cds_exon = rng.randint(first_cds_exon, n_exons - 1)
                for ei in range(first_cds_exon, last_cds_exon + 1):
                    es, ee = exon_spans[ei]
                    if ei == first_cds_exon:
                        es = es + rng.randint(0, 30)
                    if ei == last_cds_exon:
                        ee = max(es, ee - rng.randint(0, 30))
                    if ee >= es:
                        cds_spans.append((es, ee))
                        cds_len += ee - es + 1
                        n_cds += 1

            lines.append(f"{chrom}\tSIM\tgene\t{gene_start}\t{tx_end}\t.\t+\t."
                         f"\t{attr(gene_id=gid, gene_biotype='protein_coding')}\n")
            lines.append(f"{chrom}\tSIM\ttranscript\t{tx_start}\t{tx_end}\t.\t+\t."
                         f"\t{attr(gene_id=gid, transcript_id=tid)}\n")
            for es, ee in exon_spans:
                lines.append(f"{chrom}\tSIM\texon\t{es}\t{ee}\t.\t+\t."
                             f"\t{attr(gene_id=gid, transcript_id=tid)}\n")
            for es, ee in cds_spans:
                lines.append(f"{chrom}\tSIM\tCDS\t{es}\t{ee}\t.\t+\t0"
                             f"\t{attr(gene_id=gid, transcript_id=tid)}\n")

            tx_records.append((tid, cds_len, n_cds))
            cursor += rng.randint(200, 1500)

        cds_txs = [t for t in tx_records if t[2] > 0]
        if cds_txs:
            # longest cds, tiebreak on transcript_id asc
            best = sorted(cds_txs, key=lambda x: (-x[1], x[0]))[0]
            gene_to_best[gid] = best

    # insert a couple of genes whose single transcript is CDS-less to
    # exercise the "skip genes without CDS" requirement
    cursor += 2000
    for k in range(1, 4):
        gid = f"SIMN{k:03d}"
        tid = f"SIMNT{k:03d}.1"
        tx_start = cursor
        exon_end = cursor + 800
        lines.append(f"{chrom}\tSIM\tgene\t{tx_start}\t{exon_end}\t.\t+\t."
                     f"\t{attr(gene_id=gid, gene_biotype='lncRNA')}\n")
        lines.append(f"{chrom}\tSIM\ttranscript\t{tx_start}\t{exon_end}\t.\t+\t."
                     f"\t{attr(gene_id=gid, transcript_id=tid)}\n")
        lines.append(f"{chrom}\tSIM\texon\t{tx_start}\t{exon_end}\t.\t+\t."
                     f"\t{attr(gene_id=gid, transcript_id=tid)}\n")
        cursor = exon_end + 1500

    DATA.write_text("".join(lines))

    rows = sorted(gene_to_best.items(), key=lambda kv: kv[0])
    with GOLD.open("w") as fh:
        for gid, (tid, cl, nc) in rows:
            fh.write(f"{gid}\t{tid}\t{cl}\t{nc}\n")
    print(f"wrote {DATA} ({len(lines)} lines) and {GOLD} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
