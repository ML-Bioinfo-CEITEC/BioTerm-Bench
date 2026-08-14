The file `/app/data/references.fa` contains three reference genomes,
and `/app/data/reads.fastq` contains short reads.

For each read, search the read sequence **and its reverse complement**
against every reference. A reference matches if it contains the full
read exactly as a substring. Ignore reads with no matching reference.

If a read matches exactly one reference, count it as one unique read
for that reference. If it matches `k > 1` references, assign a weight
of `1/k` to each matching reference.

Write `/app/output/abundance.tsv` with header:

`reference_id<TAB>length_bp<TAB>unique_reads<TAB>ambiguous_weight<TAB>weighted_reads<TAB>rel_abundance_ppm`

`length_bp` is the reference length in bases. `weighted_reads =
unique_reads + ambiguous_weight`. `rel_abundance_ppm` is

`1e6 * (weighted_reads / length_bp) / sum_j(weighted_reads_j / length_bp_j)`.

Sort rows by `reference_id` ASCII ascending. Format
`ambiguous_weight` and `weighted_reads` with 4 decimal places and
`rel_abundance_ppm` with 6 decimal places.
