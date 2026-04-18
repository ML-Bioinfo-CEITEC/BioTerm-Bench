# BioTerm-Bench

A laptop-runnable, deterministically-graded, Harbor-compatible benchmark
of terminal bioinformatics tasks for tracking open-model progress.

> **Status — V1.1 complete.** The repository ships the three Docker
> images (`bioterm-base:v1`, `bioterm-variant:v1`,
> `bioterm-rnaseq:v1`), the validation / build / oracle-run tooling,
> CI, authoring docs, and the `scripts/new_task.sh` scaffolder. After
> the first full Harbor k=3 sweep (5 models × 30 tasks) we removed 13
> tasks that every tested model always solved and added 5 new harder
> tasks probed for weak-vs-strong model differentiation; the pack now
> has **22 tasks**. Harbor runs and rationale live in
> [docs/status.md](docs/status.md) and
> [docs/harbor-runs.md](docs/harbor-runs.md).

## What BioTerm-Bench is

A curated set of bioinformatics tasks (alignment, variant calling,
RNA-seq DE, sequence search, QC, metadata glue, and end-to-end
synthesis) that a coding agent must complete in a terminal environment.
Grading is **deterministic** — bcftools isec, set comparison, numeric
tolerance, or exact file diff. No LLM judges.

The 22 tasks currently shipping (see
[docs/status.md](docs/status.md) for the full roadmap):

| task                           | category  | grader    | image           |
| ------------------------------ | --------- | --------- | --------------- |
| `flagstat-report`              | alignment | Pattern A | bioterm-base    |
| `bam-depth-histogram`          | alignment | Pattern C | bioterm-base    |
| `sam-to-cram-roundtrip`        | alignment | Pattern A | bioterm-base    |
| `bam-mark-duplicates`          | alignment | Pattern C | bioterm-base    |
| `insert-size-stats`            | alignment | Pattern C | bioterm-base    |
| `bam-clipping-stats`           | alignment | Pattern C | bioterm-base    |
| `gtf-to-bed`                   | metadata  | Pattern A | bioterm-base    |
| `vcf-to-tsv`                   | metadata  | Pattern A | bioterm-base    |
| `fasta-rename-headers`         | metadata  | Pattern A | bioterm-base    |
| `fasta-longest-orf`            | metadata  | Pattern A | bioterm-base    |
| `gtf-longest-transcript-cds`   | metadata  | Pattern A | bioterm-base    |
| `fasta-6frame-codon-counts`    | metadata  | Pattern A | bioterm-base    |
| `fastqc-quality-report`        | qc        | Pattern C | bioterm-base    |
| `seqkit-fasta-stats`           | qc        | Pattern A | bioterm-base    |
| `vcf-split-by-type`            | variant   | Pattern D | bioterm-base    |
| `vcf-allele-frequency`         | variant   | Pattern C | bioterm-base    |
| `vcf-normalize`                | variant   | Pattern D | bioterm-base    |
| `vcf-trio-mendelian`           | variant   | Pattern C | bioterm-base    |
| `blast-best-hit`               | search    | Pattern A | bioterm-base    |
| `mafft-msa-identity`           | search    | Pattern C | bioterm-base    |
| `kmer-jaccard-matrix`          | search    | Pattern C | bioterm-base    |
| `tpm-normalize`                | rnaseq    | Pattern C | bioterm-rnaseq  |


V1 holds three commitments that override everything else:

1. **Deterministic grading only.** If a task's grader cannot be written
  in ~30 lines of bash + Python, it is not in V1.
2. **Laptop-runnable.** Full evaluation of one model against all tasks
  completes in under 5 hours on a 36 GB Apple Silicon MacBook. No
   mammalian WGS, no GPUs, no 100 GB references.
3. **Harbor-compatible.** BioTerm-Bench is a *dataset*, not a harness.
  Orchestration, logging, agent integration, and parallelism come from
   [Harbor](https://github.com/anthropics/harbor).

## Repo layout

```
bioterm-bench/
├── docker/
│   ├── bioterm-base/     # HTS stack, QC/search, R/Python, references
│   ├── bioterm-rnaseq/   # STAR / salmon / featureCounts / HTSeq (stub)
│   └── bioterm-variant/  # freebayes / VEP / SnpEff / hap.py  (stub)
├── tasks/                # one directory per task (see docs/task-authoring.md)
├── scripts/
│   ├── build_images.sh       # buildx, multi-arch
│   ├── new_task.sh           # scaffold a new task directory
│   ├── validate_task.py      # task-structure linter
│   ├── run_oracle_all.sh     # oracles must all hit reward=1
│   └── refresh_db_golds.sh   # regenerate DB golds from live APIs
├── docs/
│   ├── task-authoring.md
│   ├── grading-patterns.md
│   └── live-network-pattern.md
├── dataset.json          # Harbor dataset registration
└── .github/workflows/ci.yml
```

## Quickstart

### Build the base image (local dev, single-arch)

```bash
scripts/build_images.sh --load --only base
docker run --rm bioterm-base:v1 samtools --version | head -1
```

Multi-arch push to a registry:

```bash
GHCR_ORG=your-org scripts/build_images.sh --push
```

### Lint every task directory

```bash
python scripts/validate_task.py
```

Exits 0 with `"no tasks found"` on a clean checkout.

### Run every oracle and confirm reward=1

```bash
bash scripts/run_oracle_all.sh
```

This is the gate before release: any task that doesn't hit `reward=1`
with its own oracle solution is not shippable.

### Refresh DB-retrieval gold sets (before every eval cycle)

```bash
NCBI_API_KEY=... scripts/refresh_db_golds.sh
```

See [docs/live-network-pattern.md](docs/live-network-pattern.md).

## Running the benchmark

```bash
uv tool install harbor
# (or `pip install harbor`, whichever your environment prefers)
bash scripts/build_images.sh --only base    # and --only variant / rnaseq
export OPENAI_API_KEY=sk-...

# single-task smoke test
harbor run --path tasks/gtf-to-bed \
    --agent terminus-2 -m openai/gpt-5.4-mini --no-delete

# full current pack run
harbor run --path tasks/ \
    --agent terminus-2 -m openai/gpt-5.4-mini \
    --no-delete -n 4 -k 1
```

`--no-delete` is **required** when running with the prebuilt images in
this repo: Harbor's default `--delete` flag runs
`docker compose down --rmi all` after every trial, which would wipe the
`bioterm-*:v1` images from the local Docker engine.

For variance estimation, run each model three times (`-k 3`) and
average the per-task binary scores.

Baseline receipts — cost, wall clock, and per-task pass/fail for the
reference Harbor runs — live in
[docs/harbor-runs.md](docs/harbor-runs.md).

## Adding a task

Read [docs/task-authoring.md](docs/task-authoring.md), then pick one of
the five allowed grader shapes from [docs/grading-patterns.md](docs/grading-patterns.md).
If your task does not fit one of the five, redesign or cut it.

To jump-start the directory structure:

```bash
scripts/new_task.sh my-new-task \
    --image bioterm-base:v1 \
    --category alignment \
    --difficulty easy
```

The scaffolded task is structurally valid but intentionally fails
`validate_task.py` (TODO markers in `solve.sh`) until you fill in real
logic.

## Leaderboard (placeholder)

Numbers land once V1 tasks are authored and models are run. Reporting
format:

```
model,overall,alignment,variant,rnaseq,db,search,qc,metadata,synthesis,mean_wallclock_s,mean_tokens
anthropic/claude-opus-4-7,,,,,,,,,,
openai/gpt-5,,,,,,,,,,
deepseek-v3.2-think,,,,,,,,,,
qwen3-coder-next,,,,,,,,,,
```

## Authors & license

Vojtech Bystry and Petr Simecek. Apache 2.0 licensed — see [LICENSE](LICENSE).