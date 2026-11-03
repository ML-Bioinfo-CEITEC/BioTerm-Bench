#!/usr/bin/env bash
# Round 5: screen the batch-7 trap candidates.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
TASKS=configs/v10_round5_tasks.txt
wait_for_job() { while pgrep -f "run_bench_lane.sh $1 " > /dev/null; do sleep 60; done; }

( bash scripts/run_bench_lane.sh hardsearch5-k3-deepseek-v4-flash-thinking einfra \
      openai/deepseek-v4-flash-thinking "$TASKS" 3 2
  bash scripts/run_bench_lane.sh hardsearch5-k3-gpt-oss-120b einfra \
      openai/gpt-oss-120b "$TASKS" 3 2
) >> jobs/lane-round5-einfra.out 2>&1 &

( wait_for_job qwen38-27b-full53-k3
  wait_for_job hardsearch3-k3-qwen38-27b
  wait_for_job hardsearch4-k3-qwen38-27b
  bash scripts/run_bench_lane.sh hardsearch5-k3-qwen38-27b openrouter \
      openrouter/qwen/qwen3.8-27b "$TASKS" 3 2
) >> jobs/lane-round5-openrouter.out 2>&1 &
wait
