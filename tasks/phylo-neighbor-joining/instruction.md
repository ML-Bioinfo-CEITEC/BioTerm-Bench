`/app/data/distances.tsv` is a symmetric distance matrix over eight taxa,
with the taxon names in the header row and the first column.

Run **neighbour joining** on it and report every join.

At each step, with `n` nodes remaining and `R(x)` the sum of `x`'s distances
to all other current nodes, compute
`Q(a,b) = (n-2)*d(a,b) - R(a) - R(b)` for every pair and join the pair with
the smallest `Q`. Break ties by taking the pair whose two names, sorted
lexicographically, come first. The branch lengths are
`L(a) = d(a,b)/2 + (R(a)-R(b)) / (2*(n-2))` and `L(b) = d(a,b) - L(a)`.
The new node's distance to each remaining node `k` is
`(d(a,k) + d(b,k) - d(a,b)) / 2`. Name new nodes `N1`, `N2`, ... in join
order and repeat until two nodes remain.

Write `/app/output/nj_steps.tsv` with header

`step	node_a	node_b	len_a	len_b`

one row per join, `step` counting from 1, the two names in lexicographic
order with their own lengths, all lengths to four decimals. Add one final
row for the last two nodes with `len_a` their distance and `len_b` `0.0000`.
