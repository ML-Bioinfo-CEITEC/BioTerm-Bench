You have two protein FASTA files:

- `/app/data/proteome_a.fa`
- `/app/data/proteome_b.fa`

Find **reciprocal best hits (RBH)** between the two proteomes with
`blastp` from BLAST+:

1. Build a protein BLAST database from each FASTA (`makeblastdb -dbtype
   prot`).
2. Run `blastp` in both directions with `-outfmt 6 -num_threads 1
   -evalue 1e-5`. Exclude self-hits by construction (A and B share no
   sequence identifiers).
3. For each query, keep a **single** best hit according to the
   tie-break chain: `bitscore` descending, `evalue` ascending, subject
   id ASCII ascending.
4. A protein `a` in A and a protein `b` in B form an RBH iff `a`'s
   best hit in B is `b` AND `b`'s best hit in A is `a`.

Write the result to `/app/output/rbh.tsv` with exactly two
TAB-separated columns, **no header**:

    a_id    b_id

Rows sorted by `a_id` ASCII ascending. Trailing newline after the
last row. Grading is exact diff against gold on the (a_id, b_id)
pairs — no identity or e-value columns are required or scored.
