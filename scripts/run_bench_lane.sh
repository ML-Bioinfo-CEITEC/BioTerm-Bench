#!/usr/bin/env bash
# One benchmarking lane: a model, a task list, and a bounded retry budget.
#
#   run_bench_lane.sh <job-suffix> <provider> <model> <task-list> <k> <concurrency>
#
# Harbor resumes rather than restarts, so a relaunch never repeats a trial that
# already scored. `--no-delete` is mandatory: without it Harbor removes the
# prebuilt bioterm-* images between jobs.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SUFFIX="${1:?job suffix}"; PROVIDER="${2:?provider}"; MODEL="${3:?model}"
TASK_LIST="${4:?task list}"; ATTEMPTS="${5:?k}"; CONCURRENCY="${6:?n}"
JOBS_DIR=jobs
EINFRA_BASE="https://llm.ai.e-infra.cz/v1"
JOB_NAME="$SUFFIX"
JOB="$JOBS_DIR/$JOB_NAME"

TASK_ARGS=()
while IFS= read -r t; do
  [ -n "$t" ] || continue
  TASK_ARGS+=(--include-task-name "$t")
done < "$TASK_LIST"
EXPECTED=$(( ${#TASK_ARGS[@]} / 2 * ATTEMPTS ))

complete() {
  python3 - "$JOB" "$EXPECTED" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]) / "result.json"
if not p.exists():
    raise SystemExit(1)
d = json.loads(p.read_text())
raise SystemExit(0 if d.get("finished_at") and d.get("stats", {}).get("n_trials") == int(sys.argv[2]) else 1)
PY
}

if complete; then echo "[$(date -u +%H:%M:%SZ)] $JOB_NAME already complete"; echo "lane $SUFFIX finished"; exit 0; fi

if [ "$PROVIDER" = einfra ]; then
  set -a; . ./.env; set +a
  export OPENAI_API_KEY="${E_INFRA_API_KEY:?E_INFRA_API_KEY is required}"
else
  : "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY is required}"
fi

echo "[$(date -u +%H:%M:%SZ)] $JOB_NAME: $EXPECTED trials, k=$ATTEMPTS, n=$CONCURRENCY"
for attempt in 1 2 3 4 5; do
  if [ -d "$JOB" ] && [ -f "$JOB/result.json" ]; then
    cmd=(harbor job resume --job-path "$JOB")
  else
    cmd=(harbor run --path tasks/ --agent terminus-2 -m "$MODEL"
         --no-delete -n "$CONCURRENCY" -k "$ATTEMPTS"
         --timeout-multiplier 1.5 --job-name "$JOB_NAME"
         --jobs-dir "$JOBS_DIR" -y --artifact /tmp/terminus2)
    [ "$PROVIDER" = einfra ] && cmd+=(--ak "api_base=${EINFRA_BASE}/")
    cmd+=("${TASK_ARGS[@]}")
  fi
  "${cmd[@]}" >> "$JOBS_DIR/$JOB_NAME.log" 2>&1 || true
  if complete; then
    echo "[$(date -u +%H:%M:%SZ)] $JOB_NAME complete on attempt $attempt"
    echo "lane $SUFFIX finished"
    exit 0
  fi
  echo "[$(date -u +%H:%M:%SZ)] $JOB_NAME incomplete after attempt $attempt; cooling down"
  sleep 180
done
echo "[$(date -u +%H:%M:%SZ)] $JOB_NAME INCOMPLETE after 5 attempts"
echo "lane $SUFFIX finished"
