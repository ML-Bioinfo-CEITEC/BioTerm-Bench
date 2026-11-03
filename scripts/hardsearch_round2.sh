#!/usr/bin/env bash
# Round 2: wait for round 1's lanes, then run the full-suite benchmark and the
# discrimination screen for the nine algorithmic candidates side by side.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

wait_for() {
  local lane="$1"
  while pgrep -f "run_hardsearch_screen.sh $lane" > /dev/null; do sleep 60; done
}

# The full 53-task benchmark of the model PS asked for, on OpenRouter.
( wait_for openrouter
  bash scripts/run_bench_lane.sh qwen38-27b-full53-k3 openrouter \
      openrouter/qwen/qwen3.8-27b configs/all_tasks.txt 3 3
) >> jobs/lane-full53.out 2>&1 &

# Discrimination screen for the new algorithmic tasks, on e-INFRA.
( wait_for einfra
  bash scripts/run_bench_lane.sh hardsearch2-k3-deepseek-v4-flash-thinking einfra \
      openai/deepseek-v4-flash-thinking configs/v10_round2_tasks.txt 3 2
  bash scripts/run_bench_lane.sh hardsearch2-k3-gpt-oss-120b einfra \
      openai/gpt-oss-120b configs/v10_round2_tasks.txt 3 2
) >> jobs/lane-round2-einfra.out 2>&1 &

wait
