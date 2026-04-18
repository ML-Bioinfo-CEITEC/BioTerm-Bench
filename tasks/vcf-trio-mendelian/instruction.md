The file `/app/data/trio.vcf.gz` (with `.tbi` index) is a bgzipped VCF
with three samples in column order: `CHILD`, `FATHER`, `MOTHER`.

Count **autosomal Mendelian-violation sites**:

1. Keep only records where all of:
   - `CHROM` is autosomal (not `X/Y/MT/chrX/chrY/chrM/chrMT`).
   - `FILTER` is `PASS` (or `.`).
   - Biallelic SNV: `REF` is one base in `{A,C,G,T}`, exactly one
     `ALT` also a base in `{A,C,G,T}`.
   - No `GT` is missing in any sample (no `.` alleles).
2. Treat GTs as **unordered** (phasing ignored). Let
   `C = {c1, c2}`. The site is consistent iff
   `∃ a ∈ FATHER.GT, b ∈ MOTHER.GT : {a, b} == C`, otherwise it is
   a **violation**.

Write `/app/output/summary.json` (sorted keys, 2-space indent):

    {
      "n_sites":        <int>,
      "n_violations":   <int>,
      "violation_rate": <float, 4 dp>   # n_violations/n_sites; 0.0 if n_sites == 0
    }

Grading is exact on the two integers and `|actual - gold| <= 1e-4`
on `violation_rate`.
