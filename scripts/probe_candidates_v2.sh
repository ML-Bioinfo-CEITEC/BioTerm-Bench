#!/usr/bin/env bash
# Difficulty-probe the 5 candidate "v2" new tasks in tasks_probe2/.
# Same structure as scripts/probe_candidates.sh but over the 5 tasks
# scaffolded in the follow-up round.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p jobs
MASTER="jobs/probe-candidates-v2-master.log"
echo "=== probe v2 start $(date -Iseconds) ===" | tee "$MASTER"

run_one() {
    local job_name=$1
    local model=$2
    local log="jobs/${job_name}.log"
    echo "" | tee -a "$MASTER"
    echo "=== START ${job_name} model=${model} $(date -Iseconds) ===" | tee -a "$MASTER"
    if harbor run \
        --path tasks_probe2/ \
        --agent terminus-2 \
        -m "${model}" \
        --no-delete \
        -n 2 \
        -k 1 \
        --timeout-multiplier 1.5 \
        --job-name "${job_name}" \
        > "$log" 2>&1; then
        local rc=0
    else
        local rc=$?
    fi
    echo "=== END ${job_name} exit=${rc} $(date -Iseconds) ===" | tee -a "$MASTER"
    return 0
}

run_one probe5-gpt54nano           "openai/gpt-5.4-nano"
run_one probe5-mistral2603         "openrouter/mistralai/mistral-small-2603"
run_one probe5-gpt54mini           "openai/gpt-5.4-mini"
run_one probe5-gpt54               "openai/gpt-5.4"

echo "" | tee -a "$MASTER"
echo "=== probe v2 complete $(date -Iseconds) ===" | tee -a "$MASTER"
