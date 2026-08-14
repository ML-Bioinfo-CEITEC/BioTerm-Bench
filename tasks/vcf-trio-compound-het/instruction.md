The bgzipped VCF `/app/data/trio.vcf.gz` (with `.tbi`) has samples `CHILD`, `FATHER`, `MOTHER` and an INFO field `GENE`.

Find genes with a compound-heterozygous pattern after keeping only autosomal `PASS`/`.` biallelic SNVs with non-missing diploid `GT`.

A variant is:
- paternal if `CHILD` is heterozygous, `FATHER` carries ALT, and `MOTHER` is `0/0`;
- maternal if `CHILD` is heterozygous, `MOTHER` carries ALT, and `FATHER` is `0/0`.

Write `/app/output/compound_hets.tsv` with header:

`gene	n_paternal	n_maternal	first_paternal_pos	first_maternal_pos`

Include one row per gene having at least one paternal and one maternal variant. Sort by `gene`. `first_*_pos` is the smallest POS in that class.
