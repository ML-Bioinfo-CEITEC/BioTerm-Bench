#!/usr/bin/env bash
# Round 3: screen the batch-5 scale/multi-output candidates once the round-2
# lanes free up, on both providers.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
TASKS=configs/v10_round3_tasks.txt

wait_for_job() {
  # Wait until no lane is running the named job.
  while pgrep -f "run_bench_lane.sh $1 " > /dev/null; do sleep 60; done
}

( wait_for_job qwen38-27b-full53-k3
  bash scripts/run_bench_lane.sh hardsearch3-k3-qwen38-27b openrouter \
      openrouter/qwen/qwen3.8-27b "$TASKS" 3 2
) >> jobs/lane-round3-openrouter.out 2>&1 &

( wait_for_job hardsearch2-k3-gpt-oss-120b
  bash scripts/run_bench_lane.sh hardsearch3-k3-deepseek-v4-flash-thinking einfra \
      openai/deepseek-v4-flash-thinking "$TASKS" 3 2
  bash scripts/run_bench_lane.sh hardsearch3-k3-gpt-oss-120b einfra \
      openai/gpt-oss-120b "$TASKS" 3 2
) >> jobs/lane-round3-einfra.out 2>&1 &

wait
