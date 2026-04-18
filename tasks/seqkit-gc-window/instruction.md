The file `/app/data/seqs.fa` is a multi-record nucleotide FASTA. Some
sequences are upper case, some lower — treat them case-insensitively.

Compute **sliding-window GC percentage** per sequence:

- Window size `W = 100 bp`, step size `S = 50 bp`.
- First window starts at offset 0 (0-based, half-open); subsequent
  windows start at 50, 100, 150, ... Only emit windows whose end
  position does not exceed the sequence length — **do not** emit
  trailing partial windows.
- `gc_pct = 100 * (#G + #C in window) / len(window)`, using
  upper-case comparison. Bases that are not A/C/G/T (e.g. N) count
  against the denominator but not towards GC.
- Round `gc_pct` to 2 decimals using Python's default
  banker's-rounding (`round(x, 2)`) and format with exactly 2
  decimal places, e.g. `42.00`, `38.50`.

Write `/app/output/gc_windows.tsv` with four TAB-separated columns,
**no header**:

    seq_id    window_start    window_end    gc_pct

Sort by `seq_id` ASCII ascending, then `window_start` ascending.
`window_start` is 0-based inclusive, `window_end` is exclusive
(`window_end - window_start == 100`). Exact diff against gold.
