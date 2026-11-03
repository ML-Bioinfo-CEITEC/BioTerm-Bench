# Final 50-task BioTerm benchmark proposal

This is one benchmark organized by capability domain. Generation waves and A-D levels are not public-facing dimensions.

## Selection method

- Fit a ridge-regularized Rasch/1PL model to the complete 113 x 10 k=1 matrix.
- Use adaptive k=3 results only to exclude confirmed floor/negative items and to flag repeat stability.
- Prefer hard, informative items using 45% Rasch information, 35% hardness, and 20% item-rest monotonicity.
- Exclude confirmed floor, confirmed/uncertain negative, and clear-ceiling items.
- Keep at most one task from every A-D family and every canonical/nohint pair.
- Constrain each main domain to 6-10 tasks; include an integrated-workflow item only if psychometrically eligible.
- Cap identical k=1 response signatures at three per domain; correlation alone is not treated as semantic duplication.

With 50 slots, a median k=1 pass rate below 0.75 is impossible after the family and psychometric constraints; the selected set reaches that lower bound.

## Composition

| Domain | Tasks |
|---|---:|
| Alignment & read processing | 8 |
| Annotation & intervals | 8 |
| Quality control | 6 |
| RNA-seq & expression | 8 |
| Sequence search & comparative genomics | 10 |
| Variant & population genetics | 10 |

## Selected tasks

### Alignment & read processing

- `bam-depth-histogram` — k=1 pass 8/10; Rasch difficulty -1.91
- `bam-mark-duplicates` — k=1 pass 8/10; Rasch difficulty -1.91
- `bam-pair-orientation-stats` — k=1 pass 8/10; Rasch difficulty -1.91
- `bam-softclip-breakpoints` — k=1 pass 8/10; Rasch difficulty -1.91
- `cigar-consumption-ledger` — k=1 pass 4/10; Rasch difficulty 0.75
- `flagstat-report` — k=1 pass 8/10; Rasch difficulty -1.91
- `insert-size-stats` — k=1 pass 9/10; Rasch difficulty -3.13
- `pileup-threshold-consensus` — k=1 pass 5/10; Rasch difficulty 0.20

### Annotation & intervals

- `fasta-6frame-codon-counts` — k=1 pass 8/10; Rasch difficulty -1.91
- `grouped-interval-union` — k=1 pass 6/10; Rasch difficulty -0.40
- `gtf-cds-integrity` — k=1 pass 7/10; Rasch difficulty -1.07
- `gtf-longest-transcript-cds` — k=1 pass 9/10; Rasch difficulty -3.13
- `gtf-to-bed` — k=1 pass 8/10; Rasch difficulty -1.91
- `gtf-utr-lengths` — k=1 pass 7/10; Rasch difficulty -1.07
- `reciprocal-interval-overlap` — k=1 pass 7/10; Rasch difficulty -1.07
- `vcf-to-tsv` — k=1 pass 7/10; Rasch difficulty -1.07

### Quality control

- `depth-gc-bias-correction` — k=1 pass 8/10; Rasch difficulty -1.91
- `fastq-expected-errors` — k=1 pass 8/10; Rasch difficulty -1.91
- `fastqc-quality-report` — k=1 pass 8/10; Rasch difficulty -1.91
- `gc-window-skew` — k=1 pass 7/10; Rasch difficulty -1.07
- `seqkit-fasta-stats` — k=1 pass 9/10; Rasch difficulty -3.13
- `vcf-multisample-qc` — k=1 pass 7/10; Rasch difficulty -1.07

### RNA-seq & expression

- `counts-fisher-bh-fdr` — k=1 pass 8/10; Rasch difficulty -1.91
- `deseq-median-ratio` — k=1 pass 5/10; Rasch difficulty 0.20
- `rnaseq-deseq2-contrast` — k=1 pass 8/10; Rasch difficulty -1.91
- `rnaseq-featurecounts-matrix` — k=1 pass 7/10; Rasch difficulty -1.07
- `rnaseq-sample-qc-report` — k=1 pass 7/10; Rasch difficulty -1.07
- `rnaseq-tpm-rpkm-divergence` — k=1 pass 8/10; Rasch difficulty -1.91
- `rnaseq-tpm-top-biotype` — k=1 pass 7/10; Rasch difficulty -1.07
- `tpm-normalize` — k=1 pass 8/10; Rasch difficulty -1.91

### Sequence search & comparative genomics

- `blast-best-hit` — k=1 pass 8/10; Rasch difficulty -1.91
- `canonical-kmer-counts` — k=1 pass 6/10; Rasch difficulty -0.40
- `hmm-viterbi-segments` — k=1 pass 9/10; Rasch difficulty -3.13
- `kmer-debruijn-unitigs` — k=1 pass 7/10; Rasch difficulty -1.07
- `ortholog-rbh-clusters` — k=1 pass 7/10; Rasch difficulty -1.07
- `ortholog-synteny-blocks` — k=1 pass 9/10; Rasch difficulty -3.13
- `phylo-fitch-parsimony` — k=1 pass 8/10; Rasch difficulty -1.91
- `phylo-neighbor-joining` — k=1 pass 9/10; Rasch difficulty -3.13
- `pwm-bidirectional-scan` — k=1 pass 4/10; Rasch difficulty 0.75
- `taxonomy-score-lca` — k=1 pass 7/10; Rasch difficulty -1.07

### Variant & population genetics

- `genotype-sample-qc` — k=1 pass 6/10; Rasch difficulty -0.40
- `hwe-exact-test` — k=1 pass 4/10; Rasch difficulty 0.75
- `pairwise-ld-r2` — k=1 pass 8/10; Rasch difficulty -1.91
- `popgen-haplotype-em` — k=1 pass 6/10; Rasch difficulty -0.40
- `vcf-denovo-strict` — k=1 pass 7/10; Rasch difficulty -1.07
- `vcf-diploid-consensus` — k=1 pass 5/10; Rasch difficulty 0.20
- `vcf-phase-blocks` — k=1 pass 7/10; Rasch difficulty -1.07
- `vcf-region-variant-density` — k=1 pass 8/10; Rasch difficulty -1.91
- `vcf-trio-compound-het` — k=1 pass 7/10; Rasch difficulty -1.07
- `vcf-trio-mendelian` — k=1 pass 8/10; Rasch difficulty -1.91

## Interpretation

The Rasch estimates are screening estimates, not definitive item calibrations: there are only ten deployments and one model is intentionally bridged across two providers. A uniform confirmatory run on the frozen 50 should precede publication of final IRT parameters.
Difficulty ordering was stable in leave-one-deployment-out sensitivity analysis (minimum Spearman rho 0.895; median 0.958).

Public benchmark names omit A-D/nohint suffixes. `selected_tasks_50.csv` retains the source-task mapping needed to build the benchmark without renaming directories yet.
