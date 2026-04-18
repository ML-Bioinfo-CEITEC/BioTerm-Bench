#!/usr/bin/env bash
# One-off: full 30 tasks, k=3, OpenAI gpt-5.4-mini (same flags as run_full_benchmark_k3.sh).
# Use when the benchmark batch was started before mini was added to the main script.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p jobs
exec harbor run --path tasks/ \
  --agent terminus-2 \
  -m openai/gpt-5.4-mini \
  --no-delete -n 2 -k 3 \
  --timeout-multiplier 1.5 \
  --job-name full30-gpt54mini-k3 \
  2>&1 | tee jobs/full30-gpt54mini-k3.log
