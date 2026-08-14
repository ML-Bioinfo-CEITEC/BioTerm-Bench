The files `/app/data/species_a.fa`, `/app/data/species_b.fa`, and
`/app/data/species_c.fa` are small protein FASTAs from three species.

Find strict three-species ortholog clusters using reciprocal best
BLASTP hits:

- Compare each species pair in both directions.
- Ignore hits with `pident < 35` or `qcovs < 70`.
- For each query, keep the full best-hit set: all remaining hits whose
  bitscore equals that query's maximum bitscore after thresholding.
- A cluster `(a, b, c)` is valid only if `a↔b`, `a↔c`, and `b↔c` are all
  reciprocal best-hit-set pairs.
- Each protein may appear in at most one reported cluster. If multiple
  valid triplets share a protein, keep the lexicographically smallest
  triplet and drop later conflicting ones.

Write `/app/output/clusters.tsv` with no header, exactly three
TAB-separated columns (`species_a_id`, `species_b_id`, `species_c_id`),
sorted lexicographically by those columns.
