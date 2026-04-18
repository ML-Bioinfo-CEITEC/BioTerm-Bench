The file `/app/data/variants.vcf.gz` is a bgzip-compressed,
tabix-indexed, single-sample VCF. Only bi-allelic sites are present.

Extract a compact variant table to:

- `/app/output/variants.tsv` — a tab-separated TSV with a header row
  followed by exactly one row per VCF record (keep records in their
  original VCF order). Header (literal):

      chrom    pos    ref    alt    qual    dp    gt    vtype

  Semantics:

  - `chrom`, `pos`, `ref`, `alt` come directly from the VCF
    (`CHROM`, `POS`, `REF`, `ALT` — `ALT` is a single allele here,
    so just take it as-is).
  - `qual` is the VCF `QUAL` column, or the literal string `NA`
    if the VCF wrote `.`.
  - `dp` is the value of the `INFO/DP` tag as a string, or `NA` if
    absent.
  - `gt` is the sole sample's `FORMAT/GT` as written in the VCF
    (e.g. `0/1`, `1|1`).
  - `vtype` is `snp` if `len(ref) == 1 and len(alt) == 1`, else
    `indel`.

No trailing blank line. Integer and string values must match
byte-for-byte against the gold file.
