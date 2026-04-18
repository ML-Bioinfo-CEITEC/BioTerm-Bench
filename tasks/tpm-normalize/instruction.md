You are given two tab-separated input files.

- `/app/data/counts.tsv` — a raw-count matrix with `gene_id` in the
  first column and one column per sample (header row present). Counts
  are non-negative integers.
- `/app/data/gene_lengths.tsv` — two columns `gene_id` and `length_bp`
  (header row present). Every gene in `counts.tsv` also appears here.

Compute TPM (Transcripts Per Million) for every gene × sample cell
using the standard formula:

    RPK_{g,s} = count_{g,s} / (length_bp_g / 1000)
    scale_s   = sum_g RPK_{g,s} / 1_000_000
    TPM_{g,s} = RPK_{g,s} / scale_s

Produce one output file:

- `/app/output/tpm.tsv` — a TSV with the same columns as `counts.tsv`
  and the same row order (matching `gene_id`s in the same order). Each
  TPM value is a floating-point number. The `gene_id` column values
  must be preserved exactly. The sum of every sample's TPM column must
  be 1,000,000 (to within 1e-3 relative).
