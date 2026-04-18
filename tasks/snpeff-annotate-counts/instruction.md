You are given a VCF of SARS-CoV-2 variants and a pre-built snpEff
custom database.

- `/app/data/variants.vcf` — bi-allelic single-sample variants on
  contig `NC_045512.2`.
- `/app/data/snpeff_db/` — a snpEff data directory containing a
  genome named `SARSCoV2`. Use it via `-dataDir`.
- `/app/data/snpeff.config` — the snpEff config file that declares
  the `SARSCoV2` genome.

Annotate the VCF with snpEff, then summarise the distribution of
annotation impact classes:

    snpEff -noStats -c /app/data/snpeff.config \
        -dataDir /app/data/snpeff_db/data SARSCoV2 \
        /app/data/variants.vcf > /app/output/annotated.vcf

`snpEff` may print progress or banner lines to stdout before the VCF
body. When parsing the redirected file, **only treat a line as a VCF
data record** if it does not start with `#`, is non-empty, and splits
into at least eight tab-separated columns (`CHROM` … `INFO`). Skip all
other lines.

For every **such** data line, take the **first** `ANN=` subfield in
`INFO` and read its impact column (the third pipe-separated sub-entry,
one of `HIGH`, `MODERATE`, `LOW`, `MODIFIER`).

Produce one output file:

- `/app/output/impact_counts.json` — JSON object with exactly these
  five integer keys:

      {"HIGH": <int>, "MODERATE": <int>, "LOW": <int>,
       "MODIFIER": <int>, "total": <int>}

`total` must equal the number of VCF data lines. All counts are
exact-match against the gold.
