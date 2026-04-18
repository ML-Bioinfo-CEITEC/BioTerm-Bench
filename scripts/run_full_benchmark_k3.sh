#!/usr/bin/env bash
# Full BioTerm-Bench run: all 30 tasks, k=3, one model per job (Option B).
# Requires: bioterm-*:v1 images locally, OPENAI_API_KEY, OPENROUTER_API_KEY.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p jobs

MASTER="jobs/full-benchmark-k3-master.log"
echo "=== full benchmark k=3 start $(date -Iseconds) ===" | tee "$MASTER"

run_one() {
  local job_name=$1
  local model=$2
  echo "" | tee -a "$MASTER"
  echo "=== START ${job_name} model=${model} $(date -Iseconds) ===" | tee -a "$MASTER"
  set +e
  harbor run --path tasks/ \
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

# Cheapest / lighter models first (same order as agreed).
run_one full30-gpt54nano-k3 "openai/gpt-5.4-nano"
run_one full30-mistral2603-k3 "openrouter/mistralai/mistral-small-2603"
run_one full30-gpt-oss-120b-k3 "openrouter/openai/gpt-oss-120b"
run_one full30-qwen35122b-k3 "openrouter/qwen/qwen3.5-122b-a10b"
run_one full30-deepseek-v32-k3 "openrouter/deepseek/deepseek-v3.2"
run_one full30-kimi-k25-k3 "openrouter/moonshotai/kimi-k2.5"
run_one full30-glm5-k3 "openrouter/z-ai/glm-5"
run_one full30-glm51-k3 "openrouter/z-ai/glm-5.1"

echo "" | tee -a "$MASTER"
echo "=== full benchmark k=3 complete $(date -Iseconds) ===" | tee -a "$MASTER"
