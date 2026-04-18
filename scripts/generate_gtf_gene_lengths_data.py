#!/usr/bin/env python3
"""Generate a small chr22 GTF slice + gold gene-length table.

Picks the first N distinct gene_ids with at least one exon, writes out
every exon record for those genes as the task input, and produces a
gold TSV of (gene_id, length) where length = number of base positions
covered by the union of that gene's exons.

Outputs:
  /out/data/genes.gtf
  /out/gold/gene_lengths.tsv
"""
from __future__ import annotations

import gzip
import re
from collections import defaultdict
from pathlib import Path

GTF = "/opt/references/chr22/chr22.gtf.gz"
DATA_GTF = Path("/out/data/genes.gtf")
GOLD = Path("/out/gold/gene_lengths.tsv")
N_GENES = 12

GENE_ID_RE = re.compile(r'gene_id "([^"]+)"')


def main() -> None:
    DATA_GTF.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    chosen: list[str] = []
    with gzip.open(GTF, "rt") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 9 or cols[2] != "gene":
                continue
            m = GENE_ID_RE.search(cols[8])
            if not m:
                continue
            gid = m.group(1)
            if gid not in chosen:
                chosen.append(gid)
                if len(chosen) == N_GENES:
                    break
    chosen_set = set(chosen)

    kept: list[str] = [
        "##description: bioterm-bench gtf-gene-lengths slice\n",
        "##format: gtf\n",
    ]
    exons: dict[str, list[tuple[int, int]]] = defaultdict(list)
    with gzip.open(GTF, "rt") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 9:
                continue
            m = GENE_ID_RE.search(cols[8])
            if not m or m.group(1) not in chosen_set:
                continue
            kept.append(line)
            if cols[2] == "exon":
                start = int(cols[3])   # GTF is 1-based inclusive
                end = int(cols[4])
                exons[m.group(1)].append((start, end))

    with DATA_GTF.open("w") as fh:
        fh.writelines(kept)

    # Compute union-of-exon length per gene.
    rows: list[tuple[str, int]] = []
    for gid in chosen:
        ivs = sorted(exons[gid])
        total = 0
        cur_s, cur_e = None, None
        for s, e in ivs:
            if cur_s is None:
                cur_s, cur_e = s, e
                continue
            if s <= cur_e + 1:
                cur_e = max(cur_e, e)
            else:
                total += cur_e - cur_s + 1
                cur_s, cur_e = s, e
        if cur_s is not None:
            total += cur_e - cur_s + 1
        rows.append((gid, total))

    rows.sort()
    with GOLD.open("w") as fh:
        fh.write("gene_id\tlength\n")
        for gid, length in rows:
            fh.write(f"{gid}\t{length}\n")

    print(f"wrote {DATA_GTF} ({len(kept)} lines), {GOLD} ({len(rows)} genes)")


if __name__ == "__main__":
    main()
