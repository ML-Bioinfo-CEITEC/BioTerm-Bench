# BioTerm-Bench

A laptop-runnable, deterministically-graded, Harbor-compatible benchmark
of terminal bioinformatics tasks for tracking open-model progress.

> **Status — BioTerm-Bench v1.0 task set frozen.** The release benchmark is
> one unified set of **50 tasks** across six capability domains. The immutable
> receipt is [`configs/benchmark_v1.0_manifest.json`](configs/benchmark_v1.0_manifest.json),
> the public/source mapping is
> [`configs/benchmark_v1.0_tasks.tsv`](configs/benchmark_v1.0_tasks.tsv), and
> [`notes/v1.0-freeze.md`](notes/v1.0-freeze.md) records the decision and next
> release steps. Earlier core-25, hard-8, and candidate-wave material below is
> retained as development provenance and will be rewritten for the v1.0 paper.

## What BioTerm-Bench is

A curated set of bioinformatics tasks (alignment, variant calling,
RNA-seq DE, sequence search, QC, metadata glue, and end-to-end
synthesis) that a coding agent must complete in a terminal environment.
Grading is **deterministic** — bcftools isec, set comparison, numeric
tolerance, or exact file diff. No LLM judges.

The following table is the historical core-25 used during development, not the
v1.0 release manifest. See [`configs/benchmark_v1.0_tasks.tsv`](configs/benchmark_v1.0_tasks.tsv)
for the 50 tasks currently shipping.

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
| `fastq-per-base-quality`       | qc        | Pattern C | bioterm-base    |
| `vcf-split-by-type`            | variant   | Pattern D | bioterm-base    |
| `vcf-allele-frequency`         | variant   | Pattern C | bioterm-base    |
| `vcf-normalize`                | variant   | Pattern D | bioterm-base    |
| `vcf-trio-mendelian`           | variant   | Pattern C | bioterm-base    |
| `vcf-region-variant-density`   | variant   | Pattern C | bioterm-base    |
| `blast-best-hit`               | search    | Pattern A | bioterm-base    |
| `mafft-msa-identity`           | search    | Pattern C | bioterm-base    |
| `kmer-jaccard-matrix`          | search    | Pattern C | bioterm-base    |
| `tpm-normalize`                | rnaseq    | Pattern C | bioterm-rnaseq  |
| `rnaseq-tpm-top-biotype`       | rnaseq    | Pattern C | bioterm-rnaseq  |

The v2 candidate extension is now frozen as an 8-task hard subset, separate
from the stable core. Exact fixed-seed regeneration commands are in
[docs/v2-hard-task-regeneration.md](docs/v2-hard-task-regeneration.md).

| candidate | category | integrated capability |
| --- | --- | --- |
| `bam-splice-junction-support` | alignment | CIGAR junctions joined to GTF annotations |
| `gtf-reconstruct-translate` | metadata | genome/GTF reconstruction, strand, phase, translation |
| `vcf-diploid-consensus` | variant | phased multiallelic variants applied to both haplotypes |
| `vcf-trio-compound-het` | variant | trio inheritance and gene-level candidate aggregation |
| `vcf-multisample-qc` | variant | call rate, heterozygosity, and genotype concordance |
| `fastq-paired-adapter-qc` | qc | paired reads, adapters, orphans, and cycle summaries |
| `rnaseq-featurecounts-matrix` | rnaseq | multi-BAM feature assignment and count matrix assembly |
| `rnaseq-deseq2-contrast` | rnaseq | metadata-aware filtering, contrast, FDR, and ranking |
| `metagenome-ambiguous-abundance` | search | ambiguous mappings and fractional abundance |
| `mini-align-call-filter` | synthesis | alignment through normalized, filtered variant calls |
| `kmer-contamination-mixture` | qc | reference-specific k-mers and mixture estimation |
| `ortholog-rbh-clusters` | search | reciprocal evidence and deterministic cluster merging |

Frozen retained hard subset from `notes/v2_task_selection.json`:

- `bam-splice-junction-support`
- `vcf-diploid-consensus`
- `vcf-trio-compound-het`
- `vcf-multisample-qc`
- `rnaseq-featurecounts-matrix`
- `rnaseq-deseq2-contrast`
- `kmer-contamination-mixture`
- `ortholog-rbh-clusters`

The development receipt records 65 scored attempts, 20 scored passes, 45 scored
failures, and 7 infrastructure/protocol errors across all 12 candidates. The
retained eight account for 43 scored attempts, 15 passes, 28 failures, and 5
errors.


V1 holds three commitments that override everything else:

1. **Deterministic grading only.** If a task's grader cannot be written
  in ~30 lines of bash + Python, it is not in V1.
2. **Laptop-runnable.** Full evaluation of one model against all tasks
  completes in under 5 hours on a 36 GB Apple Silicon MacBook. No
   mammalian WGS, no GPUs, no 100 GB references.
3. **Harbor-compatible.** BioTerm-Bench is a *dataset*, not a harness.
  Orchestration, logging, agent integration, and parallelism come from
   [Harbor](https://github.com/harbor-framework/harbor).

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

### Set up the local Python environment

Use uv to install the project and its development, analysis, plotting, and
data-generation dependencies into `.venv`:

```bash
uv sync --locked --extra dev
uv run --locked --extra dev pytest -q
uv run --locked --extra dev python scripts/validate_task.py
```

Run Python scripts through `uv run --locked --extra dev` to use this environment.
Bioinformatics command-line tools and R packages are supplied by the task Docker
images built below. Harbor is installed separately as shown under
"Running the benchmark".

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

# full v1.0 run (the repository also contains non-release candidates)
benchmark_args=()
while IFS= read -r task; do
  benchmark_args+=(--include-task-name "$task")
done < configs/benchmark_tasks_50.txt
harbor run --path tasks/ "${benchmark_args[@]}" \
  --agent terminus-2 -m openai/gpt-5.4-mini \
  --no-delete -n 4 -k 1
```

`--no-delete` is **required** when running with the prebuilt images in
this repo: Harbor's default `--delete` flag runs
`docker compose down --rmi all` after every trial, which would wipe the
`bioterm-*:v1` images from the local Docker engine.

For variance estimation, the v2 reporting protocol runs every retained task
four times (`-k 4`) and reports mean reward, pass@1, and pass@4.

Baseline receipts — cost, wall clock, and per-task pass/fail for the
reference Harbor runs — live in
[docs/harbor-runs.md](docs/harbor-runs.md).

### V2 candidate selection and e-INFRA panel

```bash
# Validate all 12 candidates, then probe with the fixed development panel.
VALIDATE_ONLY=1 bash scripts/probe_v2_candidates.sh
RUN_TAG=selection bash scripts/probe_v2_candidates.sh

# Materialize the frozen retained task list from raw Harbor receipts.
python scripts/select_v2_tasks.py \
  jobs/probe-v2-selection-qwen3-14b-k2 \
  jobs/probe-v2-selection-gpt-oss-20b-k2 \
  jobs/probe-v2-selection-gemma4-26b-a4b-k2

# University provider: see docs/einfra-experiments.md first.
export EINFRA_AI_TOKEN='...'
python scripts/run_einfra_panel.py --validate-only
python scripts/run_einfra_panel.py --smoke
```

The full e-INFRA panel refuses to start until the completed frozen selection receipt
exactly matches `configs/v2_retained_tasks.txt`.

Provider cohorts and run dates are reported separately. Shared-service wall
time is operational metadata, not a model-speed benchmark.

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

## Results

Raw Harbor receipts remain under the ignored local `jobs/` directory. Generate
paper-ready cohort, model, category, and task tables with
`scripts/summarize_bioterm_v2.py`; do not combine OpenRouter and e-INFRA into a
single provider-confounded ranking. The summarizer records provider, run date,
and score scope and rejects a glob that crosses provider cohorts.

```bash
# Current core-25 OpenRouter cohort (the defaults shown explicitly).
python scripts/summarize_bioterm_v2.py \
  --pattern 'full25-k4-open-*' --provider openrouter --score-scope core-25

# Retained hard-subset e-INFRA cohort after the panel completes.
bioterm_hard_tasks=$(sed '/^#/d;/^$/d' configs/v2_retained_tasks.txt | wc -l)
python scripts/summarize_bioterm_v2.py \
  --pattern 'einfra-k4-*' --cohort-name einfra_k4_scaling \
  --expected-trials "$((4 * bioterm_hard_tasks))" --attempts-per-task 4 \
  --provider einfra --score-scope hard-subset \
  --out-dir paper/generated/einfra
```

## Authors & license

Vojtech Bystry and Petr Simecek. Apache 2.0 licensed — see [LICENSE](LICENSE).
