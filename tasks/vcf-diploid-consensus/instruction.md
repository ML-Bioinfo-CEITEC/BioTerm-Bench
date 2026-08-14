The files `/app/data/ref.fa` and `/app/data/variants.vcf.gz` (with
`.tbi`) describe a small diploid sample named `SAMPLE`.

Build two haplotype consensus sequences for every contig in the FASTA.
Apply variants left-to-right using only records where all of:

- `FILTER` is `PASS` or `.`;
- `GT` is fully phased diploid (`a|b`, no `.` alleles);
- `REF` and every `ALT` are plain DNA strings over `A/C/G/T`;
- allele indexes use the VCF convention `0 = REF`, `1..n = ALT`.

Ignore filtered, unphased, missing, or symbolic records.

For each kept record, haplotype 1 uses the left GT allele and haplotype
2 uses the right GT allele. The kept records do not overlap.

Write `/app/output/consensus.fa` with four FASTA records:

- `>chrVC1|hap1`
- `>chrVC1|hap2`
- `>chrVC2|hap1`
- `>chrVC2|hap2`

Use the reference contig order, 60-column FASTA wrapping, and a
trailing newline. Grading is exact diff against the gold FASTA.
