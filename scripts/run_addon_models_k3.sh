#!/usr/bin/env bash
# Addon batch: three models × full tasks/ pack × k=3 (75 trials per job).
# Uses OpenRouter-style IDs consistent with other Harbor scripts in this repo.
#
# Models (user names → Harbor -m):
#   google/gemma-4-26b-a4b-it     → openrouter/google/gemma-4-26b-a4b-it
#   openai/gpt-oss-20b          → openrouter/openai/gpt-oss-20b
#   qwen/qwen3.5-35b-a3b        → openrouter/qwen/qwen3.5-35b-a3b
#
# Job dirs are full25-k3-addon-* (separate from the earlier full25-k3-gemma4-26b run).
#
# Requires: bioterm-*:v1 images, OPENAI_API_KEY, OPENROUTER_API_KEY.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p jobs

TASKS_PATH="${TASKS_PATH:-tasks/}"
MASTER="jobs/addon-benchmark-k3-master.log"
echo "=== addon benchmark k=3 start $(date -Iseconds) tasks_path=${TASKS_PATH} ===" | tee "$MASTER"

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
    echo "WARN: harbor exit ${st} for ${job_name}; continuing." | tee -a "$MASTER"
  fi
}

# Light / cheaper first where possible.
run_one full25-k3-addon-gemma4-26b "openrouter/google/gemma-4-26b-a4b-it"
run_one full25-k3-addon-gpt-oss-20b "openrouter/openai/gpt-oss-20b"
run_one full25-k3-addon-qwen3535-a3b "openrouter/qwen/qwen3.5-35b-a3b"

echo "" | tee -a "$MASTER"
echo "=== addon benchmark k=3 complete $(date -Iseconds) ===" | tee -a "$MASTER"
