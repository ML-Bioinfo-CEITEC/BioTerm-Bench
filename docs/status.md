# BioTerm-Bench V1 — status

This file tracks what is shipped, what is next, and what is explicitly
deferred. It is updated alongside task PRs, not kept in the future
tense.

## Tasks shipped (13 / 30)

| # | task                        | category  | difficulty | grader    | image            | notes                                          |
|---|-----------------------------|-----------|------------|-----------|------------------|------------------------------------------------|
| 1 | `bam-sort-index`            | alignment | easy       | Pattern A | bioterm-base     | samtools sort + index, SO:coordinate check     |
| 2 | `region-extract`            | alignment | easy       | Pattern A | bioterm-base     | samtools view of genomic region                |
| 3 | `flagstat-report`           | alignment | easy       | Pattern A | bioterm-base     | 5 flagstat metrics, sorted TSV                 |
| 4 | `gtf-to-bed`                | metadata  | easy       | Pattern A | bioterm-base     | awk/sort exon extraction, deterministic sort   |
| 5 | `id-mapping`                | metadata  | easy       | Pattern A | bioterm-base     | HGNC symbol + alias resolution, offline table  |
| 6 | `vcf-stats-summary`         | metadata  | easy       | Pattern C | bioterm-base     | Ti/Tv + het/hom ratios with 1 % tolerance      |
| 7 | `fastqc-quality-report`     | qc        | easy       | Pattern C | bioterm-base     | 5 QC stats parsed out of fastqc_data.txt       |
| 8 | `vcf-filter-quality`        | variant   | easy       | Pattern D | bioterm-base     | QUAL>=30 && INFO/DP>=10 filter, bcftools isec  |
| 9 | `vcf-split-by-type`         | variant   | easy       | Pattern D | bioterm-base     | split SNVs / indels, type-purity sanity check  |
| 10 | `mpileup-call-snps`         | variant   | medium     | Pattern D | bioterm-base     | bcftools mpileup → call pipeline               |
| 11 | `blast-best-hit`            | search    | easy       | Pattern A | bioterm-base     | blastp against kinome, tie-break on bitscore   |
| 12 | `kmer-presence-grid`        | search    | easy       | Pattern A | bioterm-base     | genome × kmer presence matrix                  |
| 13 | `tpm-normalize`             | rnaseq    | easy       | Pattern C | bioterm-rnaseq   | TPM normalization, 1 % tolerance per cell      |

Every task is validated by two independent gates:

- `python3 scripts/validate_task.py` — structural linter (required
  files, TOML schema, instruction word count, `reward.txt` contract).
- `bash scripts/run_oracle_all.sh` — spins up each task's Docker
  image, runs the oracle `solution/solve.sh`, then `tests/test.sh`,
  and asserts `reward.txt == 1`.

As of the latest commit both gates pass for all 13 tasks.

## Docker images shipped

| image                 | base              | size    | what lives inside                                                             |
|-----------------------|-------------------|---------|-------------------------------------------------------------------------------|
| `bioterm-base:v1`     | debian:trixie     | 2.95 GB | samtools 1.21, bcftools 1.21, htslib 1.21, bwa-mem2 2.2.1 (amd64) / bwa (arm64), minimap2 2.28, FastQC 0.12.1, MultiQC 1.25.1, BLAST+ 2.16.0+, MAFFT 7.525, jellyfish 2.3.1, bedtools 2.31.1, seqkit 2.8.2, entrez-direct, `uv`, Python 3.12 (pysam, mygene, biopython, pandas, numpy, scipy, click, tenacity), R 4.5.3 + BiocManager (DESeq2, edgeR, limma, tximport), pre-indexed chr22, E. coli K-12, SARS-CoV-2, GIAB HG002 truth VCF, BLAST DB of the human kinome. |
| `bioterm-variant:v1`  | bioterm-base:v1   | 3.34 GB | snpEff 5.2b.                                                                  |
| `bioterm-rnaseq:v1`   | bioterm-base:v1   | 3.04 GB | STAR 2.7.11b, subread 2.0.6, salmon 1.10.2, HTSeq 2.0.5.                      |

Multi-arch (linux/amd64 + linux/arm64) builds are configured via
`scripts/build_images.sh --push`. Native arm64 builds on Apple Silicon
go through OrbStack.

## Deferred — explicitly out of scope for this PR

The tasks in the V1 spec that are **not** in this drop, and why:

- **DB-retrieval tasks (Entrez, NCBI, Ensembl REST).** These need the
  `live-network-pattern` plumbing (cached golds, rate-limit guard,
  `NCBI_API_KEY` injection) to be deterministic and safe to run in
  CI. That scaffolding exists (`scripts/refresh_db_golds.sh`) but no
  tasks depend on it yet.
- **End-to-end synthesis tasks** (full RNA-seq DE from counts, WGS
  trio Mendelian-violation analysis). These are multi-hour to author
  and grade carefully; they need their own PRs.
- **VEP 112 + chr22 offline cache.** ~20 GB on disk; provisioning it
  into `bioterm-variant` is a separate image-ops item.
- **hap.py / rtg-tools vcfeval.** Python-2 / JRE-heavy installs that
  fight with the R stack in `bioterm-base`. Will land behind a
  separate `bioterm-happy:v1` image if needed.
- **freebayes 1.3.7.** No arm64 apt package; needs a source build.
- **Prebuilt STAR index for chr22.** ~5 GB; generated at task-setup
  time in the relevant task rather than baked into the image.

## Next PR

1. Add 4–6 more tasks: BAM → depth histogram, paired-end read
   duplicate marking (Pattern C), featureCounts count-matrix-from-bams
   (needs STAR index at setup time), DESeq2 top-N DE genes (Pattern
   C), snpEff annotation counts (Pattern A), seqkit stats sanity
   (Pattern A).
2. Land the first DB-retrieval task (`entrez-gene-summary`) on top of
   the live-network pattern once caches and rate-limit guards are
   exercised in CI.
3. Multi-arch image push to GHCR behind a release tag.
