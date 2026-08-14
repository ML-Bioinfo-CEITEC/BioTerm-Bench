#!/usr/bin/env python3
"""Generate a single-sequence FASTA with a plantable ORF.

Strategy: take a chunk of the SARS-CoV-2 genome (which has real ORFs,
including the long ORF1ab), slice a window around a natural start
codon and write that slice. Then compute the longest ORF using the
definition below (6-frame, ATG -> stop, inclusive) and emit the gold
answer.

ORF semantics (must match the instruction):
- 6 reading frames: {+0, +1, +2, -0, -1, -2}; minus-strand frames are
  computed on the reverse complement of the sequence.
- An ORF begins at an ATG start codon and ends at the FIRST in-frame
  stop codon (TAA, TAG, TGA). The ORF coordinates span from the
  start of the ATG to the end of the stop codon, inclusive on both
  ends (1-based).
- Length is ORF end - ORF start + 1 (in nucleotides, includes stop).
- Tiebreak for "longest": lower strand preferred (+ before -), then
  lower frame (0<1<2), then smaller start.

Writes:
  /out/data/seq.fa
  /out/gold/orf.tsv  (single row, header: seq_id strand frame start end length)
"""
from __future__ import annotations

import gzip
from pathlib import Path

REF = "/opt/references/virus/sars_cov_2.fa.gz"
DATA = Path("/out/data/seq.fa")
GOLD = Path("/out/gold/orf.tsv")

WINDOW_START_1B = 100         # 1-based, inclusive start into sars_cov_2
WINDOW_LEN = 6000             # slice length (bp)

STOPS = {"TAA", "TAG", "TGA"}


def revcomp(s: str) -> str:
    trans = str.maketrans("ACGTN", "TGCAN")
    return s.translate(trans)[::-1]


def find_longest_orf(seq: str) -> tuple[str, int, int, int]:
    """Return (strand, frame, start_1b, end_1b) for the longest ORF."""
    L = len(seq)
    best: tuple[int, int, int, int, str] | None = None
    # Format: (-length, strand_rank, frame, start, strand_label) so that
    # sorting picks the longest; then + before - via strand_rank 0 < 1.
    for strand_rank, strand_seq in enumerate([seq, revcomp(seq)]):
        strand_label = "+" if strand_rank == 0 else "-"
        for frame in range(3):
            i = frame
            while i + 3 <= L:
                if strand_seq[i:i + 3] == "ATG":
                    # find stop
                    j = i + 3
                    while j + 3 <= L:
                        if strand_seq[j:j + 3] in STOPS:
                            orf_len = j + 3 - i
                            # Map back to forward coords:
                            if strand_rank == 0:
                                start_1b = i + 1
                                end_1b = j + 3
                            else:
                                # position in revcomp -> position in forward
                                end_1b = L - i
                                start_1b = L - (j + 3) + 1
                            candidate = (-orf_len, strand_rank, frame,
                                         start_1b, strand_label, end_1b)
                            if best is None or candidate < best[:5] + (best[5],):
                                best = candidate
                            i = j + 3   # jump past this ORF and keep scanning
                            break
                        j += 3
                    else:
                        i += 3
                        continue
                    # loop increment handled above
                else:
                    i += 3
    assert best is not None, "no ORF found in chosen window; widen the slice"
    _, strand_rank, frame, start_1b, strand_label, end_1b = best
    return strand_label, frame, start_1b, end_1b


def main() -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    GOLD.parent.mkdir(parents=True, exist_ok=True)

    with gzip.open(REF, "rt") as fh:
        header = fh.readline().rstrip("\n")
        body = "".join(line.rstrip("\n") for line in fh).upper()
    # Pull a window that is guaranteed to contain ORF1ab's body.
    slice_ = body[WINDOW_START_1B - 1: WINDOW_START_1B - 1 + WINDOW_LEN]
    assert "N" not in slice_, "unexpected N in chosen window"

    seq_id = "SARS_window"
    with DATA.open("w") as fh:
        fh.write(f">{seq_id}\n")
        for i in range(0, len(slice_), 60):
            fh.write(slice_[i:i + 60] + "\n")

    strand, frame, start_1b, end_1b = find_longest_orf(slice_)
    length = end_1b - start_1b + 1

    with GOLD.open("w") as fh:
        fh.write("seq_id\tstrand\tframe\tstart\tend\tlength\n")
        fh.write(f"{seq_id}\t{strand}\t{frame}\t{start_1b}\t{end_1b}\t{length}\n")

    print(f"wrote {DATA} (len={len(slice_)}) and gold ORF "
          f"{strand} f{frame} {start_1b}-{end_1b} len={length}")


if __name__ == "__main__":
    main()
