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
        /app/data/variants.vcf > annotated.vcf

For every annotated record, take the **first** `ANN=` subfield and
read its impact column (the third sub-entry, one of `HIGH`,
`MODERATE`, `LOW`, `MODIFIER`).

Produce one output file:

- `/app/output/impact_counts.json` — JSON object with exactly these
  five integer keys:

      {"HIGH": <int>, "MODERATE": <int>, "LOW": <int>,
       "MODIFIER": <int>, "total": <int>}

`total` must equal the number of VCF data lines. All counts are
exact-match against the gold.
