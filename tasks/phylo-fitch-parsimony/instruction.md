`/app/data/tree.newick` is a rooted binary tree over ten taxa with no
branch lengths. `/app/data/alignment.fasta` holds those ten taxa aligned
over 150 sites, all bases A, C, G or T with no gaps.

Compute the **Fitch parsimony** score of every site on this tree.

Fitch works bottom-up. Each leaf's state set is the single base that taxon
has at the site. At an internal node, take the intersection of its
children's state sets: if the intersection is non-empty, that is the node's
set and no change is counted; if it is empty, the node's set is the union
and the score increases by one. A site's score is the total number of
changes counted over the whole tree.

Write `/app/output/parsimony.tsv` with header

`site	n_distinct_bases	parsimony_score`

one row for every site, in ascending site number counting from 1, where
`n_distinct_bases` is how many different bases appear among the ten taxa at
that site and `parsimony_score` is the Fitch score. Include sites scoring
zero.
