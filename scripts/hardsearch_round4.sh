#!/usr/bin/env bash
# Round 4: screen the batch-6 long-output candidates. e-INFRA starts at once
# (its lanes are free); OpenRouter queues behind qwen's full-suite run and the
# round-3 catch-up so the machine never holds more than two lanes.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
TASKS=configs/v10_round4_tasks.txt

wait_for_job() { while pgrep -f "run_bench_lane.sh $1 " > /dev/null; do sleep 60; done; }

( bash scripts/run_bench_lane.sh hardsearch4-k3-deepseek-v4-flash-thinking einfra \
      openai/deepseek-v4-flash-thinking "$TASKS" 3 2
  bash scripts/run_bench_lane.sh hardsearch4-k3-gpt-oss-120b einfra \
      openai/gpt-oss-120b "$TASKS" 3 2
) >> jobs/lane-round4-einfra.out 2>&1 &

( wait_for_job qwen38-27b-full53-k3
  wait_for_job hardsearch3-k3-qwen38-27b
  bash scripts/run_bench_lane.sh hardsearch4-k3-qwen38-27b openrouter \
      openrouter/qwen/qwen3.8-27b "$TASKS" 3 2
) >> jobs/lane-round4-openrouter.out 2>&1 &

wait
