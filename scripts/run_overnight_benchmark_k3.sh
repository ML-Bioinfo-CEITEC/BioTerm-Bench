#!/usr/bin/env bash
# Overnight BioTerm-Bench: all tasks under tasks/, k=3 per task, one model per job.
# Skips openai/gpt-5.4 (use run_full_benchmark_k1.sh line if you need the full model).
#
# Requires: bioterm-*:v1 images locally, OPENAI_API_KEY, OPENROUTER_API_KEY.
#
# Usage:
#   bash scripts/run_overnight_benchmark_k3.sh
#   TASKS_PATH=tasks/ bash scripts/run_overnight_benchmark_k3.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p jobs

TASKS_PATH="${TASKS_PATH:-tasks/}"
MASTER="jobs/overnight-benchmark-k3-master.log"
echo "=== overnight benchmark k=3 start $(date -Iseconds) tasks_path=${TASKS_PATH} (no gpt-5.4) ===" | tee "$MASTER"

run_one() {
  local job_name=$1
  local model=$2
  echo "" | tee -a "$MASTER"
  echo "=== START ${job_name} model=${model} $(date -Iseconds) ===" | tee -a "$MASTER"
  set +e
  harbor run --path "${TASKS_PATH}" \
    --agent terminus-2 \
    -m "${model}" \
    --no-delete -n 2 -k 3 \
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

# Cheaper / lighter models first (OpenAI direct, then OpenRouter). No openai/gpt-5.4.
run_one full25-k3-gpt54nano "openai/gpt-5.4-nano"
run_one full25-k3-gpt54mini "openai/gpt-5.4-mini"
run_one full25-k3-mistral2603 "openrouter/mistralai/mistral-small-2603"
run_one full25-k3-gpt-oss-120b "openrouter/openai/gpt-oss-120b"
run_one full25-k3-qwen35122b "openrouter/qwen/qwen3.5-122b-a10b"
run_one full25-k3-deepseek-v32 "openrouter/deepseek/deepseek-v3.2"
run_one full25-k3-kimi-k25 "openrouter/moonshotai/kimi-k2.5"
run_one full25-k3-glm5 "openrouter/z-ai/glm-5"
run_one full25-k3-glm51 "openrouter/z-ai/glm-5.1"

run_one full25-k3-gemma4-26b "openrouter/google/gemma-4-26b-a4b-it"
run_one full25-k3-nemotron3-super "openrouter/nvidia/nemotron-3-super-120b-a12b"
run_one full25-k3-minimax-m27 "openrouter/minimax/minimax-m2.7"
run_one full25-k3-qwen3-32b "openrouter/qwen/qwen3-32b"
run_one full25-k3-gemma4-31b "openrouter/google/gemma-4-31b-it"

echo "" | tee -a "$MASTER"
echo "=== overnight benchmark k=3 complete $(date -Iseconds) ===" | tee -a "$MASTER"
