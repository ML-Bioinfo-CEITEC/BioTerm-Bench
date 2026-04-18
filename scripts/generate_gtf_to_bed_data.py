#!/usr/bin/env python3
"""Generate a small chr22 GTF slice + gold BED for the gtf-to-bed task.

Reads /opt/references/chr22/chr22.gtf.gz, picks the first N gene_ids it
encounters, writes out every exon for those genes as the input GTF, and
produces the corresponding gold BED6.
"""
from __future__ import annotations

import gzip
import re
import subprocess
from pathlib import Path

GTF = "/opt/references/chr22/chr22.gtf.gz"
DATA_GTF = Path("/out/data/genes.gtf")
GOLD_BED = Path("/out/gold/exons.bed")
N_GENES = 10

GENE_ID_RE = re.compile(r'gene_id "([^"]+)"')


def main() -> None:
    DATA_GTF.parent.mkdir(parents=True, exist_ok=True)
    GOLD_BED.parent.mkdir(parents=True, exist_ok=True)

    # First pass: collect the first N_GENES distinct gene_ids.
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
    kept_lines: list[str] = [
        "##description: bioterm-bench test slice of chr22\n",
        "##format: gtf\n",
        "##N_genes: " + str(len(chosen)) + "\n",
    ]
    bed_rows: list[list[str]] = []

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
            kept_lines.append(line)
            if cols[2] == "exon":
                bed_rows.append([
                    cols[0],
                    str(int(cols[3]) - 1),
                    cols[4],
                    m.group(1),
                    ".",
                    cols[6],
                ])

    with DATA_GTF.open("w") as fh:
        fh.writelines(kept_lines)

    bed_rows.sort(key=lambda r: (r[0], int(r[1]), int(r[2]), r[3]))
    with GOLD_BED.open("w") as fh:
        for r in bed_rows:
            fh.write("\t".join(r) + "\n")

    print(f"wrote {DATA_GTF} ({len(kept_lines)} lines), "
          f"{GOLD_BED} ({len(bed_rows)} exon rows)")


if __name__ == "__main__":
    main()
