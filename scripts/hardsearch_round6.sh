#!/usr/bin/env bash
# Round 6: the hint experiment. Six tasks -- three pairs that differ only by
# one sentence naming the pitfall. Same fixtures, same expected answers, so a
# pass-rate gap between a pair is attributable to the sentence alone.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
TASKS=configs/v10_round6_tasks.txt
wait_for_job() { while pgrep -f "run_bench_lane.sh $1 " > /dev/null; do sleep 60; done; }

( bash scripts/run_bench_lane.sh hardsearch6-k3-deepseek-v4-flash-thinking einfra \
      openai/deepseek-v4-flash-thinking "$TASKS" 3 2
  bash scripts/run_bench_lane.sh hardsearch6-k3-gpt-oss-120b einfra \
      openai/gpt-oss-120b "$TASKS" 3 2
) >> jobs/lane-round6-einfra.out 2>&1 &

( for j in qwen38-27b-full53-k3 hardsearch3-k3-qwen38-27b hardsearch4-k3-qwen38-27b hardsearch5-k3-qwen38-27b; do
    wait_for_job "$j"
  done
  bash scripts/run_bench_lane.sh hardsearch6-k3-qwen38-27b openrouter \
      openrouter/qwen/qwen3.8-27b "$TASKS" 3 2
) >> jobs/lane-round6-openrouter.out 2>&1 &
wait
