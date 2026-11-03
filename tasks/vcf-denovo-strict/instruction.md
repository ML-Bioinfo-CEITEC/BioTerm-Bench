`/app/data/trio.vcf.gz` (with `.tbi`) holds samples `CHILD`, `FATHER`,
`MOTHER` with `FORMAT` `GT:AD:DP`.

Find candidate *de novo* variants in the child and say which are supported.

Use only biallelic SNVs (single-base REF, one single-base ALT) on an
autosome (`chrX` excluded) with `FILTER` `PASS` or `.`.

A site is a **candidate** when `CHILD` is heterozygous (`0/1` or `1/0`) and
both parents are `0/0`. Report every candidate, classified as:

- `denovo` when all hold: `DP` at least 10 in all three samples; child
  allele balance between 0.25 and 0.75 inclusive; and ALT allelic depth
  exactly 0 in both parents;
- `uncertain` when it is a candidate but any of those fails.

Child allele balance is `AD_alt / (AD_ref + AD_alt)`.

Write `/app/output/denovo.tsv` with header

`chrom	pos	ref	alt	class	child_ab`

one row per candidate, `child_ab` to four decimals, sorted by chromosome
(`chr1` before `chr2`) then ascending position.
