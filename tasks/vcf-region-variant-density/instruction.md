Inputs:

- `/app/data/variants.vcf.gz` — bgzipped, tabix-indexed VCF. Multi-
  allelic records are possible; each `ALT` is to be counted on its own.
- `/app/data/regions.bed` — 0-based half-open BED with three columns
  (`chrom`, `start`, `end`). Intervals may overlap.

For **each BED interval in input order**, count every `(CHROM, POS,
ALT)` tuple whose `POS` (VCF 1-based) falls inside the half-open
interval `[start+1, end]`. Classify each ALT:

- `snv` if both `REF` and the specific `ALT` allele have length 1 and
  both are in `{A,C,G,T}` (case-insensitive).
- `indel` if the ALT is in `{A,C,G,T,*,}`-style bases but either
  `len(REF) != 1` or `len(ALT) != 1`. Symbolic ALTs (starting with
  `<` or containing `[`/`]`) and `*` are **ignored**.

Filter `FILTER` is ignored — count every record.

Write `/app/output/density.tsv` with this exact header line and one
row per interval (input order, duplicates preserved):

    chrom    start    end    n_snv    n_indel    density_per_kb

`density_per_kb = 1000 * (n_snv + n_indel) / (end - start)`, rounded
to 4 decimals. TAB-separated, trailing newline.

Grading: exact match on the three integer columns, `|actual - gold|
<= 1e-4` on `density_per_kb`.
