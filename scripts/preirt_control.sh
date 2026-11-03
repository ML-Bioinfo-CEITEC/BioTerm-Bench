#!/usr/bin/env bash
# Pause, resume, or inspect the resumable pre-IRT provider campaign.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1
MARKER="jobs/.preirt-paused"

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

stop_pattern() {
  local label="$1" pattern="$2" pids
  pids=$(pgrep -f "$pattern" 2>/dev/null | tr '\n' ' ')
  if [ -z "$pids" ]; then
    log "  $label: none running"
    return
  fi
  log "  $label: stopping $pids"
  # shellcheck disable=SC2086
  kill $pids 2>/dev/null || true
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    sleep 1
    pgrep -f "$pattern" >/dev/null 2>&1 || return
  done
  pids=$(pgrep -f "$pattern" 2>/dev/null | tr '\n' ' ')
  if [ -n "$pids" ]; then
    log "  $label: forcing remaining $pids"
    # shellcheck disable=SC2086
    kill -9 $pids 2>/dev/null || true
  fi
}

report() {
  python3 - <<'PY'
import json
from pathlib import Path

total_scored = total_errors = 0
for job in sorted(path for path in Path("jobs").glob("preirt-k1-*") if path.is_dir()):
    result = job / "result.json"
    if not result.exists():
        continue
    data = json.loads(result.read_text())
    trials = data.get("stats", {}).get("n_trials", 0)
    errors = data.get("stats", {}).get("n_errors", 0)
    scored = trials - errors
    total_scored += scored
    total_errors += errors
    state = "DONE" if data.get("finished_at") else "PART"
    print(f"  {state} {job.name}: scored={scored}/113 errors={errors}")
print(f"  primary matrix: {total_scored}/1130 scored cells; operational errors={total_errors}")
PY
  if [ -f "$MARKER" ]; then
    log "campaign state: PAUSED"
  elif pgrep -f 'run_preirt_panel\.py.*--phase k1|run_preirt_panel\.py.*--phase followup' >/dev/null 2>&1; then
    log "campaign state: RUNNING"
  else
    log "campaign state: IDLE (not marked paused)"
  fi
}

case "${1:-status}" in
  status)
    report
    ;;
  pause)
    mkdir -p jobs
    : > "$MARKER"
    log "pause guard created; no monitor or runner may relaunch work"
    stop_pattern "parallel-tail supervisor" 'run_preirt_parallel_tail\.sh'
    stop_pattern "pre-IRT runners" 'run_preirt_panel\.py.*--phase (k1|followup)'
    stop_pattern "pre-IRT Harbor jobs" 'harbor (run|job resume).*preirt-(k1|followup)'
    running=$(docker ps -q 2>/dev/null | tr '\n' ' ')
    if [ -n "$running" ]; then
      log "  stopping active task containers (receipts remain on disk)"
      # shellcheck disable=SC2086
      docker stop $running >/dev/null 2>&1 || true
    fi
    stop_pattern "Docker network janitor" 'docker_network_janitor\.sh'
    report
    log "resume with: bash scripts/preirt_control.sh resume"
    ;;
  resume)
    if pgrep -f 'run_preirt_panel\.py.*--phase (k1|followup)|harbor (run|job resume).*preirt-(k1|followup)' >/dev/null 2>&1; then
      log "ABORT: pre-IRT work is already running"
      report
      exit 1
    fi
    rm -f "$MARKER"
    if ! pgrep -f 'docker_network_janitor\.sh' >/dev/null 2>&1; then
      log "starting Docker network janitor"
      nohup bash scripts/docker_network_janitor.sh >> jobs/docker-network-janitor.log 2>&1 &
    fi
    log "starting resumable Qwen3.8 lane and parallel-tail supervisor"
    nohup python3 scripts/run_preirt_panel.py --provider openrouter --phase k1 \
      --only or-qwen38-27b \
      >> jobs/preirt-openrouter-runner.log 2>&1 &
    nohup bash scripts/run_preirt_parallel_tail.sh \
      >> jobs/preirt-parallel-tail.log 2>&1 &
    sleep 3
    report
    ;;
  *)
    echo "usage: bash scripts/preirt_control.sh [status|pause|resume]" >&2
    exit 2
    ;;
esac
