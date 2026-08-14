# Harbor runs

Record of end-to-end Harbor runs against the current task set. Each
entry captures: date, image tags exercised, agent + model, overall
reward, wall clock, and total API cost. Use this page as the
reproducibility receipt — if Harbor's behaviour or the tasks change,
re-run the bench and append a new entry here.

## How to run

### Prerequisites

- `docker` / OrbStack up, with `bioterm-base:v1`, `bioterm-variant:v1`,
and `bioterm-rnaseq:v1` loaded locally (see `scripts/build_images.sh`).
- `harbor` CLI on PATH (`uv tool install harbor`).
- `OPENAI_API_KEY` exported (for OpenAI models) or the equivalent key
for another LiteLLM provider.

### One-task smoke test

```bash
harbor run --path tasks/gtf-to-bed \
    --agent terminus-2 \
    -m openai/gpt-5.4-mini \
    --no-delete
```

`gtf-to-bed` is the cheapest task in the pack (pure text munging, no
aligners). Expect ~25 s wall time and ~$0.007 cost for a passing run.

### Full 30-task run

```bash
harbor run --path tasks/ \
    --agent terminus-2 \
    -m openai/gpt-5.4-mini \
    --no-delete -n 4 -k 1 \
    --job-name full30-gpt54mini
```

- `--no-delete` is mandatory while running with prebuilt images.
Harbor's default `--delete` flag runs
`docker compose down --rmi all` after every trial, which removes
the prebuilt `bioterm-*:v1` images (they come back from a cold
rebuild only).
- `-n 4` is a safe default on a laptop (Docker's parallel layer
sharing holds up fine, and the LLM bottleneck dominates anyway).
- `-k 1` means a single attempt per task; raise to `-k 3` for a more
reliable pass/fail signal at ~3x the cost.

### Oracle sanity run

To verify the benchmark itself (not the model), swap the agent:

```bash
harbor run --path tasks/ --agent oracle --no-delete -n 4
```

The oracle is Harbor's built-in agent that just runs
`solution/solve.sh`. Expect reward 1.0 on every task. If it dips,
you have a regression in either the task data or the grader.

## Run log

### 2026-04-18 — k=3 multi-model sweep on the 30-task pack

Five models sampled at `-k 3 -n 2` on the full 30-task pack (one
model per job, Option B). Intended as a first pass to check task
difficulty. Deepseek-v3.2 was **stopped partway** (13/30 tasks, 39
trials) after the aggregate signal was clear enough to act on. The
sweep directly motivated the task rebalance described at the top of
`[docs/status.md](status.md)`: **16/30 tasks had zero failed attempts
across every model**, so 13 of them were dropped in a follow-up
commit.


| model                                         | trials | pass | mean  | wall   | cost $ |
| --------------------------------------------- | ------ | ---- | ----- | ------ | ------ |
| `openai/gpt-5.4-nano`                         | 90     | 78   | 0.867 | 23 min | 0.2403 |
| `openrouter/mistralai/mistral-small-2603`     | 90     | 83   | 0.922 | 35 min | 0.6906 |
| `openrouter/openai/gpt-oss-120b`              | 90     | 74   | 0.822 | 72 min | 0.1919 |
| `openrouter/qwen/qwen3.5-122b-a10b`           | 90     | 89   | 0.989 | 45 min | 1.5926 |
| `openrouter/deepseek/deepseek-v3.2` (partial) | 39     | 38   | 0.974 | —      | 0.3898 |


Tasks that **never failed** across all five models (16) — removed or
preserved:

- Preserved (one-per-category fallback): `tpm-normalize` (rnaseq-only),
`mafft-msa-identity` (non-blast search), `vcf-normalize` (variant).
- Removed outright (13): `bam-sort-index`, `region-extract`,
`bed-merge-intervals`, `gtf-gene-lengths`, `id-mapping`,
`vcf-stats-summary`, `fastq-adapter-count`,
`fastq-length-distribution`, `kmer-presence-grid`,
`mpileup-call-snps`, `snpeff-annotate-counts`,
`vcf-filter-quality`, `vcf-intersect-bed`.

Tasks where **at least one model failed** (14, now the "informative"
core):

- Stable-ish: `mafft-msa-identity`, `vcf-normalize`,
`sam-to-cram-roundtrip`, `vcf-split-by-type`,
`vcf-allele-frequency`, `vcf-to-tsv`, `tpm-normalize`,
`fastqc-quality-report`, `seqkit-fasta-stats`.
- Differentiating: `bam-depth-histogram`, `bam-mark-duplicates`,
`flagstat-report`, `insert-size-stats`, `fasta-longest-orf`,
`fasta-rename-headers`, `gtf-to-bed`, `blast-best-hit`.

Main per-model failure modes:

- `gpt-5.4-nano` (78/90) struggled with numeric precision on
`bam-depth-histogram` and `fastqc-quality-report` (parsed the
wrong module), and with file-format edge cases on
`insert-size-stats` and `sam-to-cram-roundtrip`.
- `mistral-small-2603` (83/90) failed on `gtf-to-bed` exon ordering
and `vcf-split-by-type` INFO-parsing edge cases.
- `gpt-oss-120b` (74/90) was the weakest — multiple failures on
`fasta-longest-orf`, `fastqc-quality-report`,
`bam-mark-duplicates`, and `fasta-rename-headers` (trailing
newline / header-format drift). This model is a useful
"lower-bound" probe.
- `qwen3.5-122b-a10b` (89/90) and `deepseek-v3.2` (38/39) failed only
on `blast-best-hit`, specifically the tie-break between two
identical-score kinase hits. Suggests the instruction's tie-break
chain is still underspecified for high-capacity models.

Artefacts live under `jobs/full30-<model>-k3/`; trajectories and
config are preserved with `--no-delete`.

### 2026-04-18 — k=1 × 4-model probe of 10 new candidate tasks

Ten newly authored harder tasks were staged under `tasks_probe/` as
symlinks to `tasks/` and probed at `-k 1 -n 2` against four models
spanning weak → strong. Total probe cost: **$0.556** (well under the
$25 allotted budget).


| task                         | nano  | mistral-2603 | gpt-5.4-mini | gpt-5.4 | verdict                |
| ---------------------------- | ----- | ------------ | ------------ | ------- | ---------------------- |
| `bam-clipping-stats`         | P     | **F**        | P            | P       | kept (weak-differ)     |
| `fasta-6frame-codon-counts`  | **F** | P            | P            | P       | kept (weak-differ)     |
| `gtf-longest-transcript-cds` | **F** | P            | F*           | P       | kept (weak-differ)     |
| `vcf-trio-mendelian`         | **F** | **F**        | **F**        | P       | kept (strong-only)     |
| `kmer-jaccard-matrix`        | P     | P            | F†           | P       | kept after spec fix    |
| `blast-reciprocal-best-hits` | P     | P            | P            | P       | **dropped** (too easy) |
| `counts-median-of-ratios`    | P     | P            | P            | P       | **dropped** (too easy) |
| `counts-to-deg-ttest`        | P     | P            | P            | P       | **dropped** (too easy) |
| `fastq-quality-trim`         | P     | P            | P            | P       | **dropped** (too easy) |
| `seqkit-gc-window`           | P     | P            | P            | P       | **dropped** (too easy) |


- **F** (`gpt-5.4-mini` on `gtf-longest-transcript-cds`) was a real
error — the model dropped the leading `S` on `SIMG0001` / `SIMT0001`
ids. At `k=2` on a follow-up re-probe, mini passed 2/2, so at `k=3`
the task will still differentiate the weaker models (`nano` fails
deterministically in its single attempt).
- **F†** (`gpt-5.4-mini` on `kmer-jaccard-matrix`) was traced to spec
ambiguity: the model emitted `genome_01.fa` while the grader expected
the stripped basename `genome_01`. The instruction now explicitly
says "FASTA basenames without the `.fa` extension". A follow-up
`k=2` probe confirms mini passes cleanly after the fix; the task
was kept to balance the `search` category and because its canonical
k-mer logic still has room to trip smaller agents.

Net result: **5 new tasks shipped, 5 dropped** (plus one spec fix).
Pack size after round 1 is **17 + 5 = 22 tasks**. Probe artefacts
live under `jobs/probe10-*/` and `jobs/probe-kmer-mini-k2/`.

### 2026-04-18 — k=1 × 4-model probe, round 2 (5 candidates)

Five additional harder candidates were scaffolded to push the pack to
25 tasks and close the gap in under-represented categories (`qc`,
`rnaseq`). Same probe harness (`tasks_probe2/`, `-k 1 -n 2`, four
models). Total round-2 cost: **$0.328**.


| task                           | nano  | mistral-2603 | gpt-5.4-mini | gpt-5.4 | verdict                       |
| ------------------------------ | ----- | ------------ | ------------ | ------- | ----------------------------- |
| `vcf-region-variant-density`   | **F** | P            | **F**        | P       | kept (weak+mini fail)         |
| `rnaseq-tpm-top-biotype`       | P     | **F**        | P            | P       | kept (weak-differ)            |
| `fastq-per-base-quality`       | P     | P            | P            | P       | kept for `qc` balance (2 → 3) |
| `bam-per-contig-strand-counts` | P     | P            | P            | P       | **dropped** (too easy)        |
| `gtf-intron-gc`                | P     | P            | P            | P       | **dropped** (too easy)        |


Failure inspection:

- `vcf-region-variant-density`: nano + mini both returned
`n_indel=1` vs gold `n_indel=2` on a `chr1` interval. Both models
failed to split the multi-allelic `G,AT` record and count the
insertion ALT; a genuine parsing error.
- `rnaseq-tpm-top-biotype`: mistral emitted `ENSG100178` at rank 2
instead of `ENSG100204`; its TPM ranking / tie-break diverged from
spec.

`fastq-per-base-quality` was kept deliberately: the `qc` category
only had 2 tasks before, and a FASTQ → per-position quality table
rounds the category out even if no probe model failed it. The
`bam-per-contig-strand-counts` and `gtf-intron-gc` candidates hit
already-saturated categories (alignment 6, metadata 6), so
all-pass outcomes left no ship case for them.

Net result: **3 new tasks shipped, 2 dropped**. Final pack size is
**22 + 3 = 25 tasks**. Probe artefacts live under `jobs/probe5-*/`.

### 2026-04-18 — `openai/gpt-5.4-mini`, `terminus-2`, full 30 tasks


| metric      | value        |
| ----------- | ------------ |
| model       | gpt-5.4-mini |
| agent       | terminus-2   |
| tasks       | 30           |
| attempts    | 1 / task     |
| wall clock  | 3 m 6 s      |
| total cost  | $0.2033      |
| mean reward | 0.967        |
| pass / fail | 29 / 1       |


Per-task cost and outcome:


| task                        | reward | cost $ | in_tok | out_tok | episodes |
| --------------------------- | ------ | ------ | ------ | ------- | -------- |
| `bam-depth-histogram`       | 1      | 0.0126 | 13446  | 1757    | 5        |
| `bam-mark-duplicates`       | 1      | 0.0074 | 5388   | 1020    | 3        |
| `bam-sort-index`            | 1      | 0.0054 | 4303   | 676     | 3        |
| `bed-merge-intervals`       | 1      | 0.0047 | 2754   | 596     | 2        |
| `blast-best-hit`            | 1      | 0.0075 | 3400   | 1093    | 2        |
| `fasta-longest-orf`         | 1      | 0.0096 | 3505   | 1558    | 2        |
| `fasta-rename-headers`      | 1      | 0.0059 | 3363   | 750     | 2        |
| `fastq-adapter-count`       | 1      | 0.0047 | 2697   | 598     | 2        |
| `fastq-length-distribution` | 1      | 0.0043 | 2361   | 565     | 2        |
| `fastqc-quality-report`     | 1      | 0.0147 | 18839  | 1365    | 5        |
| `flagstat-report`           | 1      | 0.0063 | 7904   | 736     | 5        |
| `gtf-gene-lengths`          | 1      | 0.0077 | 3081   | 1202    | 2        |
| `gtf-to-bed`                | 1      | 0.0052 | 2546   | 736     | 2        |
| `id-mapping`                | 1      | 0.0070 | 4304   | 839     | 2        |
| `insert-size-stats`         | 1      | 0.0111 | 10236  | 1447    | 4        |
| `kmer-presence-grid`        | 1      | 0.0058 | 3540   | 707     | 2        |
| `mafft-msa-identity`        | 0      | 0.0081 | 3405   | 1231    | 2        |
| `mpileup-call-snps`         | 1      | 0.0043 | 2742   | 488     | 2        |
| `region-extract`            | 1      | 0.0042 | 2544   | 502     | 2        |
| `sam-to-cram-roundtrip`     | 1      | 0.0052 | 2796   | 682     | 2        |
| `seqkit-fasta-stats`        | 1      | 0.0054 | 3012   | 688     | 2        |
| `snpeff-annotate-counts`    | 1      | 0.0076 | 3257   | 1157    | 2        |
| `tpm-normalize`             | 1      | 0.0067 | 3780   | 853     | 2        |
| `vcf-allele-frequency`      | 1      | 0.0047 | 2849   | 574     | 2        |
| `vcf-filter-quality`        | 1      | 0.0051 | 4765   | 609     | 3        |
| `vcf-intersect-bed`         | 1      | 0.0051 | 2669   | 678     | 2        |
| `vcf-normalize`             | 1      | 0.0049 | 2845   | 618     | 2        |
| `vcf-split-by-type`         | 1      | 0.0056 | 4479   | 683     | 3        |
| `vcf-stats-summary`         | 1      | 0.0088 | 6786   | 1083    | 3        |
| `vcf-to-tsv`                | 1      | 0.0077 | 5287   | 828     | 3        |


Failure post-mortem:

- `mafft-msa-identity`: the model attempted
`mafft ... > /app/output/seqs.aln.fa` as its very first command,
but `/app/output` did not exist on the agent's container, so bash
refused the redirection and the task never produced an output.
This was a task-environment bug, not a model bug: 4 of the 30
trials did not `mkdir -p /app/output` before writing, and we got
unlucky on one of them. Fixed by adding
`RUN mkdir -p /app/output` to every task's
`environment/Dockerfile` (and to the
`scripts/new_task.sh` template), so `/app/output` exists as a
writable directory the moment the container starts. Re-running
the task after the fix produced reward `1.0` in 46 s.

Notable improvements vs the 17-task run on 2026-04-18 earlier in the
day:

- `id-mapping`: was the "empty-field-on-not-found" failure; agent
now reads the instruction correctly and emits the empty fields.
- `snpeff-annotate-counts`: was the parser `IndexError` failure;
agent now uses a more defensive line-splitter.

Both former failures passed without any grader change — the model is
simply more attentive on the second run, or got a luckier sampling.

### 2026-04-18 — `openai/gpt-5.4-mini`, `terminus-2`, initial 17 tasks


| metric      | value        |
| ----------- | ------------ |
| model       | gpt-5.4-mini |
| agent       | terminus-2   |
| tasks       | 17           |
| attempts    | 1 / task     |
| wall clock  | 1 m 55 s     |
| total cost  | $0.1434      |
| mean reward | 0.882        |
| pass / fail | 15 / 2       |


Per-task cost and outcome:


| task                     | reward | cost $ | in_tok | out_tok | episodes |
| ------------------------ | ------ | ------ | ------ | ------- | -------- |
| `bam-depth-histogram`    | 1      | 0.0129 | 12839  | 1494    | 5        |
| `bam-sort-index`         | 1      | 0.0061 | 2669   | 902     | 2        |
| `blast-best-hit`         | 1      | 0.0106 | 6231   | 1654    | 3        |
| `fastqc-quality-report`  | 1      | 0.0175 | 24372  | 1563    | 7        |
| `flagstat-report`        | 1      | 0.0064 | 8236   | 776     | 5        |
| `gtf-to-bed`             | 1      | 0.0086 | 8032   | 909     | 4        |
| `id-mapping`             | 0      | 0.0081 | 6340   | 1004    | 3        |
| `kmer-presence-grid`     | 1      | 0.0059 | 3420   | 740     | 2        |
| `mpileup-call-snps`      | 1      | 0.0044 | 2761   | 515     | 2        |
| `region-extract`         | 1      | 0.0047 | 2372   | 645     | 2        |
| `seqkit-fasta-stats`     | 1      | 0.0088 | 5323   | 1335    | 3        |
| `snpeff-annotate-counts` | 0      | 0.0079 | 3184   | 1219    | 2        |
| `tpm-normalize`          | 1      | 0.0061 | 3602   | 756     | 2        |
| `vcf-filter-quality`     | 1      | 0.0056 | 3778   | 605     | 2        |
| `vcf-split-by-type`      | 1      | 0.0076 | 5913   | 1040    | 3        |
| `vcf-stats-summary`      | 1      | 0.0144 | 17633  | 1687    | 5        |
| `vcf-to-tsv`             | 1      | 0.0081 | 5265   | 917     | 3        |


Failure post-mortem:

- `id-mapping`: model populated `resolved_symbol` with the query
string on rows it marked `not_found`, but the instruction requires
those two fields to be empty for `not_found`. Legitimate spec
misread.
- `snpeff-annotate-counts`: model's parser assumed every line of
`snpEff` output is a VCF record with 8+ tab columns, crashed with
`IndexError` on a non-record line. Did not recover across 2
episodes.

Both failures are graded by the deterministic verifier; neither is a
task or image bug.

## Cost projections for other runs

Tokens per task scale roughly with instruction length and debugging
depth. For `openai/gpt-5.4-mini`:

- Cheap run (30 tasks, 1 attempt): ≈ $0.20
- Reliable run (30 tasks, 3 attempts): ≈ $0.60
- Expensive models (e.g. `openai/gpt-5-pro`): multiply by the price
ratio on the [OpenAI pricing page](https://openai.com/pricing).

A local proxy model run (via `ollama` or `vllm`) is free but measures
a different thing and is not a substitute for the reference runs
above.

## Multi-model full pack, k=1 (2026-04-18)

**Script:** `scripts/run_full_benchmark_k1.sh` — runs all tasks under
`tasks/` (25-task pack) with `-k 1`, `-n 2`, `--no-delete`, same model
list as `scripts/run_full_benchmark_k3.sh` plus `openai/gpt-5.4`.

**Job name prefix:** `full25-*-k1` (one Harbor job per model).

**Logs:** `jobs/full-benchmark-k1-master.log`, `jobs/full-benchmark-k1-nohup.out`, and per-model `jobs/full25-<slug>-k1.log`.

**Models (15):** `openai/gpt-5.4-nano`, `openai/gpt-5.4-mini`, `openai/gpt-5.4`, `openrouter/mistralai/mistral-small-2603`, `openrouter/openai/gpt-oss-120b`, `openrouter/qwen/qwen3.5-122b-a10b`, `openrouter/deepseek/deepseek-v3.2`, `openrouter/moonshotai/kimi-k2.5`, `openrouter/z-ai/glm-5`, `openrouter/z-ai/glm-5.1`, `openrouter/google/gemma-4-26b-a4b-it`, `openrouter/nvidia/nemotron-3-super-120b-a12b`, `openrouter/minimax/minimax-m2.7`, `openrouter/qwen/qwen3-32b`, `openrouter/google/gemma-4-31b-it`.

**Aggregated results:** fill in after completion from each job’s
`jobs/full25-*-k1/result.json` (mean reward, pass rate, wall time,
total cost).

## Overnight multi-model, k=3, no `gpt-5.4` (2026-04-18)

**Script:** `scripts/run_overnight_benchmark_k3.sh` — full `tasks/` pack,
`-k 3`, `-n 2`, `--no-delete`, **14 models** (same sweep as the k=1
script minus `openai/gpt-5.4`).

**Job name prefix:** `full25-k3-`* (one Harbor job per model).

**Logs:** `jobs/overnight-benchmark-k3-master.log`,
`jobs/overnight-benchmark-k3-nohup.out`, and per-model
`jobs/full25-k3-<slug>.log`.

**Models (14):** `openai/gpt-5.4-nano`, `openai/gpt-5.4-mini`,
`openrouter/mistralai/mistral-small-2603`, `openrouter/openai/gpt-oss-120b`,
`openrouter/qwen/qwen3.5-122b-a10b`, `openrouter/deepseek/deepseek-v3.2`,
`openrouter/moonshotai/kimi-k2.5`, `openrouter/z-ai/glm-5`,
`openrouter/z-ai/glm-5.1`, `openrouter/google/gemma-4-26b-a4b-it`,
`openrouter/nvidia/nemotron-3-super-120b-a12b`,
`openrouter/minimax/minimax-m2.7`, `openrouter/qwen/qwen3-32b`,
`openrouter/google/gemma-4-31b-it`.

## Addon three models, k=3

**Script:** `scripts/run_addon_models_k3.sh` — same flags as the overnight
k=3 run (`tasks/`, `-k 3`, `-n 2`, `--no-delete`), **three** models only.

**Job name prefix:** `full25-k3-addon-*` (does not overwrite earlier
`full25-k3-gemma4-26b` from the 14-model sweep).

**Logs:** `jobs/addon-benchmark-k3-master.log`,
`jobs/addon-benchmark-k3-nohup.out`, `jobs/full25-k3-addon-*.log`.

**Models:** `openrouter/google/gemma-4-26b-a4b-it`,
`openrouter/openai/gpt-oss-20b`, `openrouter/qwen/qwen3.5-35b-a3b`.

## Compact open-weight sweep, k=4

**Goal:** test whether smaller open-weight / open-available models can now
saturate the 25-task pack, while keeping the wall clock near one work day.
This run uses classic averages, not the stricter "all attempts must pass"
interpretation.

**Manifest:** `configs/k4_open_8h_models.tsv`

**Runner:** `scripts/run_open_models_k4_8h.sh`

**Summarizer:** `scripts/summarize_k4_sweep.py`

**Default batch:** 9 OpenRouter models, `25 tasks x 4 attempts = 100`
trials per model, for 900 trials total. Models under 7B parameters are
excluded after `ministral-3b-2512` proved unsuitable for the benchmark.

- `openrouter/mistralai/mistral-small-3.2-24b-instruct`
- `openrouter/openai/gpt-oss-20b`
- `openrouter/qwen/qwen3-8b`
- `openrouter/qwen/qwen3-14b`
- `openrouter/qwen/qwen3-30b-a3b`
- `openrouter/qwen/qwen3.5-9b`
- `openrouter/nvidia/nemotron-nano-9b-v2`
- `openrouter/mistralai/ministral-8b-2512`
- `openrouter/mistralai/ministral-14b-2512`

**Optional overflow batch:** set `INCLUDE_OVERFLOW=1` to append:

- `openrouter/qwen/qwen3.5-27b`
- `openrouter/qwen/qwen3.5-35b-a3b`
- `openrouter/nvidia/nemotron-3-nano-30b-a3b`
- `openrouter/google/gemma-3-27b-it`

**Job name prefix:** `full25-k4-open-*`

**Logs:** `jobs/k4-open-8h-master.log` and per-model
`jobs/full25-k4-open-<slug>.log`.

**Metric definitions:**

- `mean_reward`: classic mean reward over all 100 attempts.
- `pass@1`: task success rate using the first attempt only.
- `pass@4`: task success rate if any of the four attempts succeeds.
- The headline metrics intentionally do **not** count a task as failed just
  because one of four attempts failed.

**Console workflow:**

```bash
cd /Users/petr/projects/other/BioTerm-Bench
tmux new -s bioterm-k4
bash scripts/run_open_models_k4_8h.sh
```

Detach from `tmux` without stopping the run: press `Ctrl-b`, then `d`.

Reattach:

```bash
tmux attach -t bioterm-k4
```

Watch progress from another terminal:

```bash
tail -f jobs/k4-open-8h-master.log
```

Validate the manifest without running Harbor:

```bash
VALIDATE_ONLY=1 bash scripts/run_open_models_k4_8h.sh
```

Run a one-model smoke test:

```bash
ONLY_MODELS=gpt-oss-20b bash scripts/run_open_models_k4_8h.sh
```

Resume after interruption; completed jobs are skipped by default:

```bash
SKIP_COMPLETED=1 bash scripts/run_open_models_k4_8h.sh
```

Start from a specific manifest slug:

```bash
START_FROM=qwen3-14b bash scripts/run_open_models_k4_8h.sh
```

Run only selected manifest slugs:

```bash
ONLY_MODELS=ministral3b,qwen3-8b bash scripts/run_open_models_k4_8h.sh
```

Run with overflow models:

```bash
INCLUDE_OVERFLOW=1 bash scripts/run_open_models_k4_8h.sh
```

Summarize after jobs finish:

```bash
python3 scripts/summarize_k4_sweep.py
```

This writes:

- `jobs/k4-open-8h-models.csv`
- `jobs/k4-open-8h-tasks.csv`

## V2 hard-task and e-INFRA protocol (2026-08-12)

The completed small-model k=4 runs exposed a ceiling on the core-25 pack.
BioTerm-Bench v2 therefore stages 12 multi-stage candidates and selects 6–8 by
a fixed development probe rather than retaining every authored task.

Development panel (two attempts per candidate):

| role | exact model ID |
| --- | --- |
| weak | `openrouter/qwen/qwen3-14b` |
| middle | `openrouter/openai/gpt-oss-20b` |
| strong | `openrouter/google/gemma-4-26b-a4b-it` |

The selector requires both a pass and failure and a pooled scored pass rate in
`[0.10, 0.80]`; Harbor exceptions and missing verifier rewards are errors, not
scored failures. The generated receipt is `notes/v2_task_selection.json`.

Resume behavior was exercised against the completed 24-trial GPT-OSS
development job with `harbor job resume --job-path`: Harbor reported 24/24 and
the number of per-trial result files remained exactly 24 before and after the
command. The manifest runner uses the same resume operation for incomplete
e-INFRA jobs.

The e-INFRA scaling cohort uses exact IDs, k=4, Terminus-2, one sequential model
job, and at most two concurrent trials. It is reported separately from
OpenRouter because provider, deployment, and run date differ. The e-INFRA
service is shared, so its wall time is recorded only as operational metadata.
See `docs/einfra-experiments.md` for credential handling, monitoring, and resume
rules.

### Existing anomaly exclusion

`full25-k4-open-mistral-small-31-24b` is not a zero-capability result. All 100
attempts ended in `AgentTimeoutError`; the job accumulated 278,873,813 input
tokens and $99.10745103 reported cost. The v2 analysis excludes it from model
score tables under the protocol-error rule while retaining it in error
accounting.
