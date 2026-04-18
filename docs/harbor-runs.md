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

### 2026-04-18 — `openai/gpt-5.4-mini`, `terminus-2`, full 30 tasks

| metric        | value        |
|---------------|--------------|
| model         | gpt-5.4-mini |
| agent         | terminus-2   |
| tasks         | 30           |
| attempts      | 1 / task     |
| wall clock    | 3 m 6 s      |
| total cost    | $0.2033      |
| mean reward   | 0.967        |
| pass / fail   | 29 / 1       |

Per-task cost and outcome:

| task | reward | cost $ | in_tok | out_tok | episodes |
|---|---:|---:|---:|---:|---:|
| `bam-depth-histogram` | 1 | 0.0126 | 13446 | 1757 | 5 |
| `bam-mark-duplicates` | 1 | 0.0074 | 5388 | 1020 | 3 |
| `bam-sort-index` | 1 | 0.0054 | 4303 | 676 | 3 |
| `bed-merge-intervals` | 1 | 0.0047 | 2754 | 596 | 2 |
| `blast-best-hit` | 1 | 0.0075 | 3400 | 1093 | 2 |
| `fasta-longest-orf` | 1 | 0.0096 | 3505 | 1558 | 2 |
| `fasta-rename-headers` | 1 | 0.0059 | 3363 | 750 | 2 |
| `fastq-adapter-count` | 1 | 0.0047 | 2697 | 598 | 2 |
| `fastq-length-distribution` | 1 | 0.0043 | 2361 | 565 | 2 |
| `fastqc-quality-report` | 1 | 0.0147 | 18839 | 1365 | 5 |
| `flagstat-report` | 1 | 0.0063 | 7904 | 736 | 5 |
| `gtf-gene-lengths` | 1 | 0.0077 | 3081 | 1202 | 2 |
| `gtf-to-bed` | 1 | 0.0052 | 2546 | 736 | 2 |
| `id-mapping` | 1 | 0.0070 | 4304 | 839 | 2 |
| `insert-size-stats` | 1 | 0.0111 | 10236 | 1447 | 4 |
| `kmer-presence-grid` | 1 | 0.0058 | 3540 | 707 | 2 |
| `mafft-msa-identity` | 0 | 0.0081 | 3405 | 1231 | 2 |
| `mpileup-call-snps` | 1 | 0.0043 | 2742 | 488 | 2 |
| `region-extract` | 1 | 0.0042 | 2544 | 502 | 2 |
| `sam-to-cram-roundtrip` | 1 | 0.0052 | 2796 | 682 | 2 |
| `seqkit-fasta-stats` | 1 | 0.0054 | 3012 | 688 | 2 |
| `snpeff-annotate-counts` | 1 | 0.0076 | 3257 | 1157 | 2 |
| `tpm-normalize` | 1 | 0.0067 | 3780 | 853 | 2 |
| `vcf-allele-frequency` | 1 | 0.0047 | 2849 | 574 | 2 |
| `vcf-filter-quality` | 1 | 0.0051 | 4765 | 609 | 3 |
| `vcf-intersect-bed` | 1 | 0.0051 | 2669 | 678 | 2 |
| `vcf-normalize` | 1 | 0.0049 | 2845 | 618 | 2 |
| `vcf-split-by-type` | 1 | 0.0056 | 4479 | 683 | 3 |
| `vcf-stats-summary` | 1 | 0.0088 | 6786 | 1083 | 3 |
| `vcf-to-tsv` | 1 | 0.0077 | 5287 | 828 | 3 |

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

| metric        | value        |
|---------------|--------------|
| model         | gpt-5.4-mini |
| agent         | terminus-2   |
| tasks         | 17           |
| attempts      | 1 / task     |
| wall clock    | 1 m 55 s     |
| total cost    | $0.1434      |
| mean reward   | 0.882        |
| pass / fail   | 15 / 2       |

Per-task cost and outcome:

| task                       | reward | cost $ | in_tok | out_tok | episodes |
|----------------------------|-------:|-------:|-------:|--------:|---------:|
| `bam-depth-histogram`      |      1 | 0.0129 |  12839 |    1494 |        5 |
| `bam-sort-index`           |      1 | 0.0061 |   2669 |     902 |        2 |
| `blast-best-hit`           |      1 | 0.0106 |   6231 |    1654 |        3 |
| `fastqc-quality-report`    |      1 | 0.0175 |  24372 |    1563 |        7 |
| `flagstat-report`          |      1 | 0.0064 |   8236 |     776 |        5 |
| `gtf-to-bed`               |      1 | 0.0086 |   8032 |     909 |        4 |
| `id-mapping`               |      0 | 0.0081 |   6340 |    1004 |        3 |
| `kmer-presence-grid`       |      1 | 0.0059 |   3420 |     740 |        2 |
| `mpileup-call-snps`        |      1 | 0.0044 |   2761 |     515 |        2 |
| `region-extract`           |      1 | 0.0047 |   2372 |     645 |        2 |
| `seqkit-fasta-stats`       |      1 | 0.0088 |   5323 |    1335 |        3 |
| `snpeff-annotate-counts`   |      0 | 0.0079 |   3184 |    1219 |        2 |
| `tpm-normalize`            |      1 | 0.0061 |   3602 |     756 |        2 |
| `vcf-filter-quality`       |      1 | 0.0056 |   3778 |     605 |        2 |
| `vcf-split-by-type`        |      1 | 0.0076 |   5913 |    1040 |        3 |
| `vcf-stats-summary`        |      1 | 0.0144 |  17633 |    1687 |        5 |
| `vcf-to-tsv`               |      1 | 0.0081 |   5265 |     917 |        3 |

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
