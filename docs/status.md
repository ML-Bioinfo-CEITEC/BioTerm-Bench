# BioTerm-Bench V1 — status

This file tracks what is shipped, what is next, and what is explicitly
deferred. It is updated alongside task PRs, not kept in the future
tense.

## Tasks shipped (30 / 30)

| #  | task                        | category  | difficulty | grader    | image            | notes                                          |
|----|-----------------------------|-----------|------------|-----------|------------------|------------------------------------------------|
|  1 | `bam-sort-index`            | alignment | easy       | Pattern A | bioterm-base     | samtools sort + index, SO:coordinate check     |
|  2 | `region-extract`            | alignment | easy       | Pattern A | bioterm-base     | samtools view + sort/dup-count enforcement     |
|  3 | `flagstat-report`           | alignment | easy       | Pattern A | bioterm-base     | 5 flagstat metrics, sorted TSV                 |
|  4 | `bam-depth-histogram`       | alignment | easy       | Pattern C | bioterm-base     | samtools depth -a → mean/median/covered frac   |
|  5 | `sam-to-cram-roundtrip`     | alignment | easy       | Pattern A | bioterm-base     | BAM → CRAM (+index); grader samtools-views back|
|  6 | `bam-mark-duplicates`       | alignment | easy       | Pattern C | bioterm-base     | samtools markdup, exact duplicate count         |
|  7 | `insert-size-stats`         | alignment | easy       | Pattern C | bioterm-base     | mean + stdev insert size from `samtools stats`  |
|  8 | `gtf-to-bed`                | metadata  | easy       | Pattern A | bioterm-base     | awk/sort exon extraction, 4-key sort           |
|  9 | `gtf-gene-lengths`          | metadata  | easy       | Pattern A | bioterm-base     | union-of-exon length per gene, sorted TSV       |
| 10 | `id-mapping`                | metadata  | easy       | Pattern A | bioterm-base     | HGNC symbol + alias resolution, offline table  |
| 11 | `vcf-to-tsv`                | metadata  | easy       | Pattern A | bioterm-base     | pysam extract of CHROM/POS/REF/ALT/QUAL/DP/GT  |
| 12 | `vcf-stats-summary`         | metadata  | easy       | Pattern C | bioterm-base     | Ti/Tv + het/hom ratios, per-ALT counting       |
| 13 | `fasta-rename-headers`      | metadata  | easy       | Pattern A | bioterm-base     | rename FASTA ids from a mapping TSV             |
| 14 | `bed-merge-intervals`       | metadata  | easy       | Pattern A | bioterm-base     | bedtools merge with 50 bp slop, strict sort     |
| 15 | `fasta-longest-orf`         | metadata  | medium     | Pattern A | bioterm-base     | 6-frame longest ORF, explicit tiebreak          |
| 16 | `fastqc-quality-report`     | qc        | easy       | Pattern C | bioterm-base     | 5 QC stats parsed out of fastqc_data.txt       |
| 17 | `seqkit-fasta-stats`        | qc        | easy       | Pattern A | bioterm-base     | per-sequence length / GC% / N%, 2-decimal TSV  |
| 18 | `fastq-adapter-count`       | qc        | easy       | Pattern A | bioterm-base     | substring-match adapter occurrence count        |
| 19 | `fastq-length-distribution` | qc        | easy       | Pattern A | bioterm-base     | length → count histogram, sorted TSV            |
| 20 | `vcf-filter-quality`        | variant   | easy       | Pattern D | bioterm-base     | QUAL>=30 && INFO/DP>=10 filter, bcftools isec  |
| 21 | `vcf-split-by-type`         | variant   | easy       | Pattern D | bioterm-base     | split SNVs / indels, type-purity sanity check  |
| 22 | `mpileup-call-snps`         | variant   | medium     | Pattern D | bioterm-base     | bcftools mpileup → call pipeline               |
| 23 | `snpeff-annotate-counts`    | variant   | medium     | Pattern A | bioterm-variant  | snpEff + bundled SARS-CoV-2 DB, impact tally   |
| 24 | `vcf-allele-frequency`      | variant   | easy       | Pattern C | bioterm-base     | AF per record from AD, tol-per-row compare      |
| 25 | `vcf-intersect-bed`         | variant   | easy       | Pattern D | bioterm-base     | bcftools view -R, VCF-set equality              |
| 26 | `vcf-normalize`             | variant   | medium     | Pattern D | bioterm-base     | bcftools norm -m -any, split + left-align       |
| 27 | `blast-best-hit`            | search    | easy       | Pattern A | bioterm-base     | blastp against kinome, deterministic tiebreak  |
| 28 | `kmer-presence-grid`        | search    | easy       | Pattern A | bioterm-base     | genome × kmer presence matrix                  |
| 29 | `mafft-msa-identity`        | search    | medium     | Pattern C | bioterm-base     | MAFFT + pairwise identity on upper triangle     |
| 30 | `tpm-normalize`             | rnaseq    | easy       | Pattern C | bioterm-rnaseq   | TPM normalization, 1 % tolerance per cell      |

Every task is validated by two independent gates:

- `python3 scripts/validate_task.py` — structural linter (required
  files, TOML schema, instruction word count, `reward.txt` contract).
- `bash scripts/run_oracle_all.sh` — spins up each task's Docker
  image, runs the oracle `solution/solve.sh`, then `tests/test.sh`,
  and asserts `reward.txt == 1`. Pass `--skip-missing-images` to
  tolerate images that are not locally loaded.

As of the latest commit both gates pass for all 30 tasks. All three
images (`bioterm-base`, `bioterm-variant`, `bioterm-rnaseq`) are
exercised by at least one real task.

## Task-authoring scaffolding

`scripts/new_task.sh` produces a new task directory populated with
skeleton `task.toml`, `instruction.md`, `solve.sh`, `test.sh`, and
`check.py`. The skeleton intentionally fails `validate_task.py`
(TODO markers in `solve.sh`) so that an unfinished task cannot be
silently merged. CI runs the scaffolder as a smoke test on every PR.

## Docker images shipped

| image                 | base              | size    | what lives inside                                                             |
|-----------------------|-------------------|---------|-------------------------------------------------------------------------------|
| `bioterm-base:v1`     | debian:trixie     | 2.95 GB | samtools 1.21, bcftools 1.21, htslib 1.21, bwa-mem2 2.2.1 (amd64) / bwa (arm64), minimap2 2.28, FastQC 0.12.1, MultiQC 1.25.1, BLAST+ 2.16.0+, MAFFT 7.525, jellyfish 2.3.1, bedtools 2.31.1, seqkit 2.8.2, entrez-direct, `uv`, Python 3.12 (pysam, mygene, biopython, pandas, numpy, scipy, click, tenacity), R 4.5.3 + BiocManager (DESeq2, edgeR, limma, tximport), pre-indexed chr22, E. coli K-12, SARS-CoV-2, GIAB HG002 truth VCF, BLAST DB of the human kinome. |
| `bioterm-variant:v1`  | bioterm-base:v1   | 3.34 GB | snpEff 5.2b (task-level DBs are shipped per-task under `data/snpeff_db/`).    |
| `bioterm-rnaseq:v1`   | bioterm-base:v1   | 3.04 GB | STAR 2.7.11b, subread 2.0.6, salmon 1.10.2, HTSeq 2.0.5.                      |

Multi-arch (linux/amd64 + linux/arm64) builds are configured via
`scripts/build_images.sh --push`. Native arm64 builds on Apple Silicon
go through OrbStack.

## Hardening pass (for weaker-model robustness)

The following task specs were made more explicit during the last
authoring cycle. Each change makes the instruction easier to follow
for a smaller model while keeping grading deterministic:

- `vcf-stats-summary`: disambiguated "one per line" → per-ALT-allele
  counting for n_records / n_snps / n_indels, and per-VCF-line for
  het_hom.
- `kmer-presence-grid`: dropped the contradictory "ignore N
  positions" clause (k-mers are ACGT-only so Ns simply cannot
  match).
- `blast-best-hit`: made the tie-break chain explicit (bitscore desc,
  evalue asc, sseqid ASCII asc) and updated the oracle accordingly.
- `fastqc-quality-report`: clarified that the Q20 fraction is
  computed per-row of the `Per base sequence quality` module, which
  may be a single position or a bin.
- `region-extract`: grader now enforces coordinate-sortedness and
  record-count equality (previously the set-based name check could
  silently accept duplicates).

## Harbor compatibility

Each task ships an `environment/Dockerfile` (one-line `FROM <image>`
so Harbor's Docker backend has a valid build definition) and an
`environment/docker-compose.yaml` that bind-mounts the task's own
`data/` onto `/app/data` and `gold/` onto `/gold`. This keeps Harbor's
agent/verifier pipeline identical to `scripts/run_oracle_all.sh`
without duplicating any inputs. `scripts/validate_task.py` enforces
both files.

Two external Harbor runs have been recorded against this task pack on
2026-04-18 with `terminus-2` + `openai/gpt-5.4-mini`, 1 attempt per
task:

- Initial 17 tasks: **15 / 17** passed in 1 m 55 s, $0.14 total spend.
- Full 30 tasks (post-expansion): **29 / 30** passed (mean reward
  0.967) in 3 m 6 s, $0.20 total spend. The single failure
  (`mafft-msa-identity`) was a task-environment bug — `/app/output`
  was not pre-created, so a redirection-first agent strategy
  crashed before producing any output. Fixed by having every
  task's `environment/Dockerfile` `RUN mkdir -p /app/output`; a
  targeted re-run scored 1.0.

Per-task breakdowns and post-mortems live in
[`docs/harbor-runs.md`](harbor-runs.md).

Operational note: Harbor's default `--delete` flag runs
`docker compose down --rmi all` after every trial, which removes
prebuilt `bioterm-*:v1` images. Always pass `--no-delete` when
running against the local images in this repo.

## Deferred — explicitly out of scope for this PR

- **DB-retrieval tasks (Entrez, NCBI, Ensembl REST).** Scaffolding
  (`scripts/refresh_db_golds.sh`, `docs/live-network-pattern.md`)
  exists but no task depends on it yet. Needs cached golds, a
  rate-limit guard, and `NCBI_API_KEY` wiring exercised in CI.
- **End-to-end synthesis tasks** (full RNA-seq DE from counts, WGS
  trio Mendelian-violation analysis). Multi-hour to author and grade
  carefully; each gets its own PR.
- **VEP 112 + chr22 offline cache.** ~20 GB on disk; provisioning it
  into `bioterm-variant` is a separate image-ops item.
- **hap.py / rtg-tools vcfeval.** Python-2 / JRE-heavy installs that
  conflict with the R stack in `bioterm-base`. Candidates for a
  dedicated `bioterm-happy:v1` image if needed.
- **freebayes 1.3.7.** No arm64 apt package; needs a source build.
- **Prebuilt STAR index for chr22.** ~5 GB; generated at task-setup
  time in the relevant task rather than baked into the image.

## Next PR

1. Land the first DB-retrieval task (`entrez-gene-summary`) on top of
   the live-network pattern once caches and rate-limit guards are
   exercised in CI.
2. A second RNA-seq-heavy task (featureCounts / DESeq2 top-N DE
   genes) once the STAR chr22 index is scripted into task setup.
3. Multi-arch image push to GHCR behind a release tag.
4. Cross-model Harbor run at N=10 attempts × 5–10 models to surface
   systematic failure patterns per task.
