Use `/app/data/calls.vcf.gz` (with `.tbi`) and `/app/data/pairs.tsv`.

Keep only autosomal `PASS`/`.` biallelic SNVs. For every sample, compute:
- `n_sites`: number of kept sites
- `n_called`: non-missing diploid `GT`
- `call_rate = n_called / n_sites`
- `n_het`: heterozygous called sites
- `het_rate = n_het / n_called` (0 if `n_called == 0`)

For every pair in `pairs.tsv`, compare only kept sites where both samples are called. Convert each genotype to ALT dosage (`0/0 -> 0`, het -> 1, `1/1 -> 2`). Concordance is the fraction with identical dosage.

Write:

- `/app/output/sample_qc.tsv` with header `sample	n_sites	n_called	call_rate	n_het	het_rate`
- `/app/output/pair_concordance.tsv` with header `sample_a	sample_b	n_compared	concordance`

Keep sample order from the VCF and pair order from `pairs.tsv`. Format floats to 4 decimals.
