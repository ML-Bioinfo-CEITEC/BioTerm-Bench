`/app/data/reads.fasta` holds error-free 120-base reads, all from the
forward strand of one linear sequence.

Build a de Bruijn graph with **k = 21** and report its unitigs.

Nodes are the distinct 20-mers; every distinct 21-mer in the reads is one
edge, from its first 20 bases to its last 20. Ignore reverse complements
and count each distinct 21-mer once.

Call a node **simple** when it has exactly one incoming and exactly one
outgoing edge. A unitig is a maximal path of edges whose every *interior*
node is simple; each edge belongs to exactly one unitig. Spell a unitig by
taking its first node's 20 bases and then the final base of each edge along
the path.

Write `/app/output/unitigs.tsv` with header

`unitig_id	length	n_kmers	sequence`

sorted by descending `length`, ties broken by ascending `sequence`. Number
them `unitig001`, `unitig002`, ... in that order. `n_kmers` is the number of
edges in the unitig.
