`/app/data/genotypes.tsv` gives, for five independent locus pairs, 200
individuals each with their unphased genotypes at two biallelic loci as an
alternate-allele count of 0, 1 or 2.

Estimate the four haplotype frequencies for each locus pair by **EM**.

Label haplotypes `0-0`, `0-1`, `1-0`, `1-1` by their alleles at locus 1 and
locus 2. Every genotype combination determines an individual's two
haplotypes uniquely except the double heterozygote (1 and 1), which is
either `0-0` plus `1-1` or `0-1` plus `1-0`.

Start every frequency at `0.25` and run exactly **200 iterations**. In each
iteration, split each double heterozygote between the two possibilities in
proportion to `2*f(0-0)*f(1-1)` and `2*f(0-1)*f(1-0)` using the current
frequencies, then set each new frequency to that haplotype's expected count
divided by 400.

Write `/app/output/haplotype_freqs.tsv` with header

`pair_id	haplotype	frequency`

twenty rows, sorted by `pair_id` then by haplotype in the order above,
frequencies to six decimals.
