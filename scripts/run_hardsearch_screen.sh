#!/usr/bin/env bash
# Screen the v1.0 hard candidates against a small, deliberately spread panel.
#
# One small/fast model and two e-INFRA models at the ends of the current
# ability range, so a candidate can be judged on *discrimination*: a task the
# strongest model always solves is not a candidate, and neither is one the
# weakest model never solves.
#
#   bash scripts/run_hardsearch_screen.sh openrouter
#   bash scripts/run_hardsearch_screen.sh einfra
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LANE="${1:?usage: run_hardsearch_screen.sh <openrouter|einfra>}"
JOBS_DIR="jobs"
ATTEMPTS=3
CONCURRENCY=2
TASK_LIST="configs/v10_candidates.txt"
MONITOR="$JOBS_DIR/hardsearch-monitor.jsonl"
EINFRA_BASE="https://llm.ai.e-infra.cz/v1"

mkdir -p "$JOBS_DIR"

TASK_ARGS=()
while IFS= read -r t; do
  [ -n "$t" ] || continue
  TASK_ARGS+=(--include-task-name "$t")
done < "$TASK_LIST"
N_TASKS=$(( ${#TASK_ARGS[@]} / 2 ))
EXPECTED=$(( N_TASKS * ATTEMPTS ))

note() {
  python3 - "$MONITOR" "$1" "$2" "$3" <<'PY'
import json, sys
from datetime import datetime, timezone
path, event, job, extra = sys.argv[1:5]
with open(path, "a") as fh:
    fh.write(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "event": event, "job": job, "detail": extra,
    }, sort_keys=True) + "\n")
PY
}

# A job is done when Harbor wrote result.json with the full trial count.
job_complete() {
  python3 - "$1" "$EXPECTED" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]) / "result.json"
if not p.exists():
    raise SystemExit(1)
d = json.loads(p.read_text())
ok = bool(d.get("finished_at")) and d.get("stats", {}).get("n_trials") == int(sys.argv[2])
raise SystemExit(0 if ok else 1)
PY
}

run_model() {
  local slug="$1" model="$2" provider="$3"
  local job_name="hardsearch-k${ATTEMPTS}-${slug}"
  local job="$JOBS_DIR/$job_name"

  if job_complete "$job"; then
    echo "[$(date -u +%H:%M:%SZ)] $job_name already complete"
    return 0
  fi

  local -a cmd
  if [ -d "$job" ] && [ -f "$job/result.json" ]; then
    cmd=(harbor job resume --job-path "$job")
  else
    cmd=(harbor run --path tasks/ --agent terminus-2 -m "$model"
         --no-delete -n "$CONCURRENCY" -k "$ATTEMPTS"
         --timeout-multiplier 1.5 --job-name "$job_name"
         --jobs-dir "$JOBS_DIR" -y --artifact /tmp/terminus2)
    if [ "$provider" = einfra ]; then
      cmd+=(--ak "api_base=${EINFRA_BASE}/")
    fi
    cmd+=("${TASK_ARGS[@]}")
  fi

  note start "$job_name" "$model"
  echo "[$(date -u +%H:%M:%SZ)] starting $job_name ($model)"
  # Three bounded attempts: a transient provider fault should not cost the lane.
  local rc=0
  for attempt in 1 2 3; do
    "${cmd[@]}" >>"$JOBS_DIR/$job_name.log" 2>&1 || rc=$?
    if job_complete "$job"; then
      note complete "$job_name" "attempt=$attempt"
      echo "[$(date -u +%H:%M:%SZ)] $job_name complete"
      return 0
    fi
    note retry "$job_name" "attempt=$attempt rc=$rc"
    sleep 300
    cmd=(harbor job resume --job-path "$job")
  done
  note incomplete "$job_name" "rc=$rc"
  echo "[$(date -u +%H:%M:%SZ)] $job_name INCOMPLETE"
  return 0
}

case "$LANE" in
  openrouter)
    : "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY is required}"
    run_model qwen38-27b openrouter/qwen/qwen3.8-27b openrouter
    ;;
  einfra)
    set -a; . ./.env; set +a
    export OPENAI_API_KEY="${E_INFRA_API_KEY:?E_INFRA_API_KEY is required}"
    run_model deepseek-v4-flash-thinking openai/deepseek-v4-flash-thinking einfra
    run_model gpt-oss-120b openai/gpt-oss-120b einfra
    ;;
  *) echo "unknown lane: $LANE" >&2; exit 2 ;;
esac
echo "[$(date -u +%H:%M:%SZ)] lane $LANE finished"
