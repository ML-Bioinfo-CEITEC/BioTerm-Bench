# Task authoring

Every task in BioTerm-Bench V1 is a self-contained directory under `tasks/`.
This document is the contract: if `scripts/validate_task.py` rejects your
task, re-read this file.

Related:

- [grading-patterns.md](grading-patterns.md) — the five grader patterns V1 allows
- [live-network-pattern.md](live-network-pattern.md) — for the four DB-retrieval tasks

## Required layout

```
tasks/<task-id>/
├── task.toml              Harbor metadata
├── instruction.md         what the agent reads (< 200 words)
├── solution/
│   └── solve.sh           oracle solution (must achieve reward=1)
├── tests/
│   ├── test.sh            Harbor entry point; writes /logs/verifier/reward.txt
│   └── check.py           grading logic
├── data/                  inputs the agent sees at /app/data/ (read-only)
├── gold/                  expected outputs (mounted read-only at /gold)
└── offline_fixtures/      optional; only for DB tasks under BIOTERM_OFFLINE=1
```

Task IDs are kebab-case and unique across the benchmark.

## `task.toml`

```toml
version = "1.0"

[metadata]
author_name  = "Your Name"
author_email = "you@example.com"
difficulty   = "easy"        # easy | medium | hard
category     = "alignment"   # alignment | variant | rnaseq | db
                             # | search | qc | metadata | synthesis
tags         = ["samtools", "bam"]

[verifier]
timeout_sec = 120.0

[agent]
timeout_sec = 600.0

[environment]
build_timeout_sec = 600.0
docker_image      = "bioterm-base:v1"  # or -rnaseq / -variant
cpus              = 4
memory            = "8G"
storage           = "10G"
```

DB-retrieval tasks additionally set `network = "restricted"` and
`allowed_hosts = [...]`; see [live-network-pattern.md](live-network-pattern.md).

## `instruction.md`

- Second person, imperative mood. "Produce a file called X at Y containing Z."
- State every output path and filename exactly. Vague instructions break grading.
- State the output schema when applicable (columns, JSON keys, sort order).
- State acceptable tolerance qualitatively if relevant, but **never reveal
  the numeric grading thresholds**. Threshold leakage makes the benchmark
  too easy.
- Do **not** hint at which tool to use unless the task specifically tests a
  named tool.
- Keep under 200 words. Agents don't read long instructions carefully.

Example:

```markdown
The file `/app/data/unsorted.sam` is an unsorted SAM file.

Produce two output files:
- `/app/output/sample.sorted.bam` — coordinate-sorted BAM
- `/app/output/sample.sorted.bam.bai` — index for the sorted BAM

The output files must pass `samtools quickcheck`.
```

## `tests/test.sh`

The Harbor entry point. Must write `1` to `/logs/verifier/reward.txt` on
pass and `0` on fail. Keep it this simple:

```bash
#!/bin/bash
set -euo pipefail
mkdir -p /logs/verifier
if python3 /tests/check.py; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
```

## `tests/check.py`

The grading logic. Exit 0 on pass, non-zero on fail. Use one of the five
patterns in [grading-patterns.md](grading-patterns.md). No dependencies
beyond the standard library + `pysam` / `pandas` (already in the base image).
Readable in under a minute.

## `solution/solve.sh`

The oracle. Achieving `reward=1` with `solve.sh` is the author's proof that
the task is solvable and gradable as specified. `scripts/run_oracle_all.sh`
runs every oracle before release.

Rules:

- Must start with a shebang (`#!/usr/bin/env bash` or similar).
- No `TODO` markers — the validator rejects them.
- Writes outputs to `/app/output/` at the paths named in `instruction.md`.
- May read from `/app/data/` and `/opt/references/`. It must **not** read
  from `/gold/` (the grader does that).

## Data sizing

Keep task inputs small so the whole suite fits a 36 GB laptop:

| kind            | size budget per task |
|-----------------|----------------------|
| FASTQ total     | < 50 MB              |
| BAM             | < 100 MB             |
| count matrix    | < 5 MB               |
| VCF             | < 10 MB              |

Synthetic inputs must be generated from a fixed random seed. Commit the
generator to `scripts/generate_<task-id>_data.py`.

## Validation workflow

```bash
python scripts/validate_task.py --only <task-id>     # structural lint
bash   scripts/run_oracle_all.sh --only <task-id>    # oracle must hit reward=1
```

Both must pass before a task can be merged.
