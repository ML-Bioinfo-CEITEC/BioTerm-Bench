# BioTerm-Bench

A laptop-runnable, deterministically-graded, Harbor-compatible benchmark
of terminal bioinformatics tasks for tracking open-model progress.

> **Status — V1 in progress.** This repository currently holds the
> infrastructure (Docker base image, validation/build/oracle-run tooling,
> CI, authoring docs). Task content lands in subsequent PRs.

## What BioTerm-Bench is

A curated set of **30 bioinformatics tasks** (alignment, variant calling,
RNA-seq DE, public-DB retrieval, sequence search, QC, metadata glue, and
end-to-end synthesis) that a coding agent must complete in a terminal
environment. Grading is **deterministic** — bcftools isec, hap.py, set
comparison, numeric tolerance, or exact file diff. No LLM judges.

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
pip install harbor-bench
docker pull ghcr.io/<org>/bioterm-base:v1
docker pull ghcr.io/<org>/bioterm-rnaseq:v1
docker pull ghcr.io/<org>/bioterm-variant:v1

harbor dataset register bioterm-bench-core --path ./bioterm-bench
harbor run -d bioterm-bench-core -m anthropic/claude-opus-4-7 -a terminus -n 1
```

For variance estimation, run each model three times and average the
per-task binary scores.

## Adding a task

Read [docs/task-authoring.md](docs/task-authoring.md), then pick one of
the five allowed grader shapes from [docs/grading-patterns.md](docs/grading-patterns.md).
If your task does not fit one of the five, redesign or cut it.

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

Vojtech Bystry and Petr Simecek. MIT licensed — see [LICENSE](LICENSE).
