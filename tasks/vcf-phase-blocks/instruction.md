`/app/data/phased.vcf.gz` (with `.tbi`) is a single-sample VCF. Some records
carry a phased genotype and a `PS` (phase set) value; others are unphased or
homozygous and carry no `PS`.

Summarise the haplotype blocks.

Use only records whose genotype is **phased and heterozygous** -- the `GT`
separator is `|` and the two alleles differ -- and which have a `PS` value.
A block is all such records sharing a chromosome and a `PS` value.

Report only blocks holding at least two variants.

Write `/app/output/phase_blocks.tsv` with header

`chrom	phase_set	n_variants	start	end	span	max_gap`

where `start` and `end` are the smallest and largest positions in the block,
`span` is `end - start + 1`, and `max_gap` is the largest difference between
consecutive positions in the block. Sort by chromosome (`chr1` before
`chr2`) then ascending `phase_set`.
