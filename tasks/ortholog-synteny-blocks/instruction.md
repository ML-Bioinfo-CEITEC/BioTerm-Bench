`/app/data/orthologs.tsv` lists one-to-one ortholog pairs between two
genomes, with each gene's chromosome and its integer order index along that
chromosome. The rows are shuffled.

Chain the pairs into syntenic blocks.

Work through each genome-A chromosome in ascending `index_a`. Two
consecutive pairs continue the same block when they map to the **same**
genome-B chromosome and their `index_b` values differ by at least 1 and at
most 3. A block must keep a consistent direction: once a block has two
members, every later step must have the same sign of `index_b` change as the
step before it. Any pair that fails these tests starts a new block.

Report only blocks containing at least three pairs.

Write `/app/output/synteny_blocks.tsv` with header

`chrom_a	chrom_b	orientation	n_pairs	start_a	end_a`

where `orientation` is `+` when `index_b` rises across the block and `-`
when it falls, and `start_a`/`end_a` are the first and last `index_a`.
Sort by `chrom_a` then `start_a`.
