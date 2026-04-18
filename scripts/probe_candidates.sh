#!/usr/bin/env bash
# Difficulty-probe the 10 candidate new tasks in tasks_probe/.
# For each model, runs k=1 so we can see which tasks differentiate
# weak models (expect failures) from strong models (expect passes).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p jobs

MASTER="jobs/probe-candidates-master.log"
echo "=== probe start $(date -Iseconds) ===" | tee "$MASTER"

run_one() {
  local job_name=$1
  local model=$2
  echo "" | tee -a "$MASTER"
  echo "=== START ${job_name} model=${model} $(date -Iseconds) ===" | tee -a "$MASTER"
  set +e
  harbor run --path tasks_probe/ \
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
    echo "WARN: harbor exit ${st} for ${job_name}; continuing." | tee -a "$MASTER"
  fi
}

# Weak probes: we want at least one model to fail each task.
run_one probe10-gpt54nano           "openai/gpt-5.4-nano"
run_one probe10-mistral2603         "openrouter/mistralai/mistral-small-2603"

# Strong probes: we want at least one to succeed each task.
run_one probe10-gpt54mini           "openai/gpt-5.4-mini"
run_one probe10-gpt54                "openai/gpt-5.4"

echo "" | tee -a "$MASTER"
echo "=== probe complete $(date -Iseconds) ===" | tee -a "$MASTER"
