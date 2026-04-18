#!/usr/bin/env bash
# One-off: the five extra OpenRouter models added after the main k=3 batch.
# Same flags as run_full_benchmark_k3.sh. Use if the long-running benchmark
# was started before these lines were added to the main script.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p jobs
MASTER="jobs/full-benchmark-extra-openrouter-k3.log"
echo "=== extra OpenRouter k=3 start $(date -Iseconds) ===" | tee "$MASTER"

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
    echo "WARN: harbor exit ${st} for ${job_name}; continuing." | tee -a "$MASTER"
  fi
}

run_one full30-gemma4-26b-k3 "openrouter/google/gemma-4-26b-a4b-it"
run_one full30-nemotron3-super-k3 "openrouter/nvidia/nemotron-3-super-120b-a12b"
run_one full30-minimax-m27-k3 "openrouter/minimax/minimax-m2.7"
run_one full30-qwen3-32b-k3 "openrouter/qwen/qwen3-32b"
run_one full30-gemma4-31b-k3 "openrouter/google/gemma-4-31b-it"

echo "" | tee -a "$MASTER"
echo "=== extra OpenRouter k=3 complete $(date -Iseconds) ===" | tee -a "$MASTER"
