#!/usr/bin/env python3
"""Generate fixtures for kmer-contamination-mixture."""
from __future__ import annotations

import gzip
import os
import random
from pathlib import Path

SEED = 20260812
READ_LEN = 75
K = 17
BASES = "ACGT"
COMP = str.maketrans("ACGT", "TGCA")


def out_root() -> Path:
    return Path(os.environ.get("BIOTERM_OUT_ROOT", "/out"))


def rand_seq(n: int, rng: random.Random) -> str:
    return "".join(rng.choice(BASES) for _ in range(n))


def revcomp(seq: str) -> str:
    return seq.translate(COMP)[::-1]


def write_fasta(path: Path, name: str, seq: str) -> None:
    with path.open("w") as fh:
        fh.write(f">{name}\n")
        for i in range(0, len(seq), 60):
            fh.write(seq[i:i + 60] + "\n")


def canonical_kmers(seq: str, k: int) -> set[str]:
    s = seq.upper()
    out: set[str] = set()
    for i in range(len(s) - k + 1):
        kmer = s[i:i + k]
        if any(base not in BASES for base in kmer):
            continue
        out.add(min(kmer, revcomp(kmer)))
    return out


def assignment_counts(refs: dict[str, str], reads: list[str]) -> list[tuple[str, int, str]]:
    ref_sets = {name: canonical_kmers(seq, K) for name, seq in refs.items()}
    owners: dict[str, set[str]] = {}
    for name, kmers in ref_sets.items():
        for kmer in kmers:
            owners.setdefault(kmer, set()).add(name)
    specific = {
        name: {kmer for kmer in kmers if owners[kmer] == {name}}
        for name, kmers in ref_sets.items()
    }

    counts = {name: 0 for name in refs}
    counts["ambiguous"] = 0
    counts["unassigned"] = 0

    for read in reads:
        scores = {name: 0 for name in refs}
        for i in range(len(read) - K + 1):
            kmer = read[i:i + K].upper()
            if any(base not in BASES for base in kmer):
                continue
            ck = min(kmer, revcomp(kmer))
            for name in refs:
                if ck in specific[name]:
                    scores[name] += 1
        best = max(scores.values())
        if best == 0:
            counts["unassigned"] += 1
            continue
        winners = sorted(name for name, score in scores.items() if score == best)
        if len(winners) != 1:
            counts["ambiguous"] += 1
            continue
        counts[winners[0]] += 1

    total = len(reads)
    order = ["alpha", "beta", "gamma", "delta", "ambiguous", "unassigned"]
    return [(label, counts[label], f"{counts[label] / total:.4f}") for label in order]


def build_specific_sets(refs: dict[str, str]) -> dict[str, set[str]]:
    ref_sets = {name: canonical_kmers(seq, K) for name, seq in refs.items()}
    owners: dict[str, set[str]] = {}
    for name, kmers in ref_sets.items():
        for kmer in kmers:
            owners.setdefault(kmer, set()).add(name)
    return {
        name: {kmer for kmer in kmers if owners[kmer] == {name}}
        for name, kmers in ref_sets.items()
    }


def score_read(read: str, refs: dict[str, str], specific: dict[str, set[str]]) -> dict[str, int]:
    scores = {name: 0 for name in refs}
    for i in range(len(read) - K + 1):
        kmer = read[i:i + K].upper()
        if any(base not in BASES for base in kmer):
            continue
        ck = min(kmer, revcomp(kmer))
        for name in refs:
            if ck in specific[name]:
                scores[name] += 1
    return scores


def find_tied_read(
    refs: dict[str, str],
    specific: dict[str, set[str]],
    left: str,
    right: str,
    rng: random.Random,
) -> str:
    left_seq = refs[left]
    right_seq = refs[right]
    for _ in range(20000):
        a_len = rng.randint(31, 44)
        b_len = READ_LEN - a_len
        a_start = rng.randint(0, len(left_seq) - a_len)
        b_start = rng.randint(0, len(right_seq) - b_len)
        read = left_seq[a_start:a_start + a_len] + right_seq[b_start:b_start + b_len]
        scores = score_read(read, refs, specific)
        best = max(scores.values())
        winners = sorted(name for name, score in scores.items() if score == best and best > 0)
        if winners == sorted([left, right]) and scores[left] == scores[right]:
            return read
        rc = revcomp(read)
        scores = score_read(rc, refs, specific)
        best = max(scores.values())
        winners = sorted(name for name, score in scores.items() if score == best and best > 0)
        if winners == sorted([left, right]) and scores[left] == scores[right]:
            return rc
    raise RuntimeError(f"failed to find tied read for {left}/{right}")


def main() -> None:
    root = out_root()
    data_dir = root / "data"
    gold_dir = root / "gold"
    refs_dir = data_dir / "references"
    refs_dir.mkdir(parents=True, exist_ok=True)
    gold_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)

    shared_ab = rand_seq(180, rng)
    shared_cd = rand_seq(170, rng)

    refs = {
        "alpha": rand_seq(420, rng) + shared_ab + rand_seq(680, rng),
        "beta": rand_seq(390, rng) + shared_ab + rand_seq(710, rng),
        "gamma": rand_seq(450, rng) + shared_cd + rand_seq(650, rng),
        "delta": rand_seq(430, rng) + shared_cd + rand_seq(670, rng),
    }
    specific = build_specific_sets(refs)
    for name, seq in refs.items():
        write_fasta(refs_dir / f"{name}.fa", name, seq)

    reads: list[str] = []

    def sample_reads(name: str, n: int) -> None:
        seq = refs[name]
        for _ in range(n):
            start = rng.randint(0, len(seq) - READ_LEN)
            read = seq[start:start + READ_LEN]
            if rng.random() < 0.5:
                read = revcomp(read)
            reads.append(read)

    for name, n in [("alpha", 210), ("beta", 110), ("gamma", 60), ("delta", 30)]:
        sample_reads(name, n)

    # Shared-region reads: no reference-specific kmers, so unassigned.
    for _ in range(16):
        start = rng.randint(0, len(shared_ab) - READ_LEN)
        reads.append(shared_ab[start:start + READ_LEN])
    for _ in range(12):
        start = rng.randint(0, len(shared_cd) - READ_LEN)
        reads.append(shared_cd[start:start + READ_LEN])

    tied_ab = find_tied_read(refs, specific, "alpha", "beta", rng)
    tied_gd = find_tied_read(refs, specific, "gamma", "delta", rng)
    for _ in range(8):
        reads.append(tied_ab)
    for _ in range(6):
        reads.append(tied_gd)

    # A few noisy reads become unassigned after invalid windows are skipped.
    for _ in range(8):
        core = list(refs["beta"][rng.randint(0, len(refs["beta"]) - READ_LEN):][:READ_LEN])
        for idx in rng.sample(range(READ_LEN), 18):
            core[idx] = "N"
        reads.append("".join(core))

    with gzip.open(data_dir / "reads.fastq.gz", "wt") as fh:
        for idx, seq in enumerate(reads, start=1):
            fh.write(f"@mix_{idx:04d}\n{seq}\n+\n{'I' * len(seq)}\n")

    rows = assignment_counts(refs, reads)
    ambiguous_count = next(count for label, count, _frac in rows if label == "ambiguous")
    if ambiguous_count == 0:
        raise RuntimeError("expected non-zero ambiguous reads")
    with (gold_dir / "mixture.tsv").open("w") as fh:
        fh.write("label\tread_count\tfraction\n")
        for label, count, frac in rows:
            fh.write(f"{label}\t{count}\t{frac}\n")

    print(
        f"wrote {len(refs)} references, {len(reads)} reads, and mixture gold; "
        f"ambiguous={ambiguous_count}"
    )


if __name__ == "__main__":
    main()
