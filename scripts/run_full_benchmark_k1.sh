#!/usr/bin/env bash
# Full BioTerm-Bench run: all tasks under tasks/, k=1, one model per job.
# Use this for a single-attempt sweep across many models (cheaper than k=3).
#
# Requires: bioterm-*:v1 images locally, OPENAI_API_KEY, OPENROUTER_API_KEY.
#
# Usage:
#   bash scripts/run_full_benchmark_k1.sh
#   TASKS_PATH=tasks/ bash scripts/run_full_benchmark_k1.sh   # default
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p jobs

TASKS_PATH="${TASKS_PATH:-tasks/}"
MASTER="jobs/full-benchmark-k1-master.log"
echo "=== full benchmark k=1 start $(date -Iseconds) tasks_path=${TASKS_PATH} ===" | tee "$MASTER"

run_one() {
  local job_name=$1
  local model=$2
  echo "" | tee -a "$MASTER"
  echo "=== START ${job_name} model=${model} $(date -Iseconds) ===" | tee -a "$MASTER"
  set +e
  harbor run --path "${TASKS_PATH}" \
    --agent terminus-2 \
    -m "${model}" \
    --no-delete -n 2 -k 1 \
    --timeout-multiplier 1.5 \
    --job-name "${job_name}" \
    2>&1 | tee "jobs/${job_name}.log"
  local st=$?
  set -e
  echo "=== END ${job_name} exit=${st} $(date -Iseconds) ===" | tee -a "$MASTER"
  if [[ $st -ne 0 ]]; then
    echo "WARN: harbor exit ${st} for ${job_name}; continuing with next model." | tee -a "$MASTER"
  fi
}

# Cheaper / lighter models first (OpenAI direct, then OpenRouter).
run_one full25-gpt54nano-k1 "openai/gpt-5.4-nano"
run_one full25-gpt54mini-k1 "openai/gpt-5.4-mini"
run_one full25-gpt54-k1 "openai/gpt-5.4"
run_one full25-mistral2603-k1 "openrouter/mistralai/mistral-small-2603"
run_one full25-gpt-oss-120b-k1 "openrouter/openai/gpt-oss-120b"
run_one full25-qwen35122b-k1 "openrouter/qwen/qwen3.5-122b-a10b"
run_one full25-deepseek-v32-k1 "openrouter/deepseek/deepseek-v3.2"
run_one full25-kimi-k25-k1 "openrouter/moonshotai/kimi-k2.5"
run_one full25-glm5-k1 "openrouter/z-ai/glm-5"
run_one full25-glm51-k1 "openrouter/z-ai/glm-5.1"

# Extra OpenRouter models (ids verified on openrouter.ai/api/v1/models).
run_one full25-gemma4-26b-k1 "openrouter/google/gemma-4-26b-a4b-it"
run_one full25-nemotron3-super-k1 "openrouter/nvidia/nemotron-3-super-120b-a12b"
run_one full25-minimax-m27-k1 "openrouter/minimax/minimax-m2.7"
run_one full25-qwen3-32b-k1 "openrouter/qwen/qwen3-32b"
run_one full25-gemma4-31b-k1 "openrouter/google/gemma-4-31b-it"

echo "" | tee -a "$MASTER"
echo "=== full benchmark k=1 complete $(date -Iseconds) ===" | tee -a "$MASTER"
