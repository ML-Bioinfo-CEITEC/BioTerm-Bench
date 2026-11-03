`/app/data/sequence.fasta` holds one 4000-base sequence.
`/app/data/model.tsv` gives a two-state HMM: each row is a state with its
initial probability, its transition probabilities to `AT_rich` and
`GC_rich`, and its emission probabilities for A, C, G and T.

Decode the sequence with the **Viterbi** algorithm and report the state
segments.

Work in log space. Multiplying 4000 probabilities underflows to zero in
double precision and silently produces a wrong path.

Should two states ever tie exactly, prefer the one listed first in
`model.tsv`.

Collapse the decoded path into maximal runs of one state.

Write `/app/output/segments.tsv` with header

`start	end	state	length`

one row per run, in ascending `start`, where `start` and `end` are 1-based
inclusive positions along the sequence and `length` is `end - start + 1`.
The runs must tile the whole sequence with no gap and no overlap.
