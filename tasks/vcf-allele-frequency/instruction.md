The file `/app/data/calls.vcf.gz` (with index
`/app/data/calls.vcf.gz.tbi`) is a bi-allelic, single-sample VCF. The
`FORMAT/AD` field is present on every record and holds two integers
`ref_depth,alt_depth`.

Produce one output file:

- `/app/output/af.tsv` — tab-separated with the exact header
  `CHROM\tPOS\tAF`. Each subsequent row has three columns:
    - `CHROM`: the chromosome string from the VCF,
    - `POS`: 1-based position (integer, as in the VCF),
    - `AF`: the allele frequency, formatted to **exactly 6 decimal
      places**, computed as

          AF = alt_depth / (ref_depth + alt_depth)

Rules:

- Skip any VCF record where `ref_depth + alt_depth == 0`. These rows
  must not appear in the output.
- Preserve the record order as it appears in the VCF (do not sort).
- No blank lines, no comment lines.

Tolerance: AF values are compared with small numeric tolerance, so
minor rounding differences are acceptable, but the set of
`(CHROM, POS)` rows in the output must match the gold exactly.
