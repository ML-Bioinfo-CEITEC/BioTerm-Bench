#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output /tmp/rbh

python3 - <<'PY'
import csv
import subprocess
from pathlib import Path

TMP = Path("/tmp/rbh")
TMP.mkdir(parents=True, exist_ok=True)
PAIRS = [
    ("A", Path("/app/data/species_a.fa"), "B", Path("/app/data/species_b.fa")),
    ("A", Path("/app/data/species_a.fa"), "C", Path("/app/data/species_c.fa")),
    ("B", Path("/app/data/species_b.fa"), "C", Path("/app/data/species_c.fa")),
]


def run_blast(query: Path, subject: Path, out_path: Path) -> None:
    db = TMP / f"{subject.stem}_db"
    subprocess.check_call([
        "makeblastdb", "-dbtype", "prot", "-in", str(subject), "-out", str(db)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.check_call([
        "blastp",
        "-query", str(query),
        "-db", str(db),
        "-outfmt", "6 qseqid sseqid pident qcovs bitscore",
        "-max_target_seqs", "20",
        "-evalue", "1e-6",
        "-out", str(out_path),
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def best_hit_sets(tsv: Path) -> dict[str, set[str]]:
    best: dict[str, tuple[float, set[str]]] = {}
    with tsv.open() as fh:
        for row in csv.reader(fh, delimiter="\t"):
            if not row:
                continue
            q, s, pident, qcovs, bitscore = row
            if float(pident) < 35.0 or float(qcovs) < 70.0:
                continue
            score = float(bitscore)
            prev = best.get(q)
            if prev is None:
                best[q] = (score, {s})
            else:
                prev_score, prev_subjects = prev
                if score > prev_score:
                    best[q] = (score, {s})
                elif score == prev_score:
                    prev_subjects.add(s)
    return {q: subjects for q, (_score, subjects) in best.items()}


rbh = {}
for left_label, left_fa, right_label, right_fa in PAIRS:
    fwd = TMP / f"{left_label}_to_{right_label}.tsv"
    rev = TMP / f"{right_label}_to_{left_label}.tsv"
    run_blast(left_fa, right_fa, fwd)
    run_blast(right_fa, left_fa, rev)
    fwd_best = best_hit_sets(fwd)
    rev_best = best_hit_sets(rev)
    rbh[(left_label, right_label)] = {
        q: sorted(
            s for s in subjects
            if q in rev_best.get(s, set())
        )
        for q, subjects in fwd_best.items()
    }

triplets = []
for a, bs in rbh[("A", "B")].items():
    cs = rbh[("A", "C")].get(a)
    if not cs:
        continue
    for b in bs:
        bc = set(rbh[("B", "C")].get(b, []))
        for c in cs:
            if c in bc:
                triplets.append((a, b, c))

triplets.sort()
used = set()
kept = []
for triplet in triplets:
    if any(protein in used for protein in triplet):
        continue
    kept.append(triplet)
    used.update(triplet)

with open("/app/output/clusters.tsv", "w") as fh:
    for triplet in kept:
        fh.write("\t".join(triplet) + "\n")
PY
