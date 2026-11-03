#!/usr/bin/env bash
# Pause, resume, or inspect the append-only BioTerm-Bench v1 campaign.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1
MARKER="jobs/.v1-panel-paused"

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

stop_pattern() {
  local label="$1" pattern="$2" pids
  pids=$(pgrep -f "$pattern" 2>/dev/null | tr '\n' ' ')
  if [ -z "$pids" ]; then log "  $label: none running"; return; fi
  log "  $label: stopping $pids"
  # shellcheck disable=SC2086
  kill $pids 2>/dev/null || true
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    sleep 1
    pgrep -f "$pattern" >/dev/null 2>&1 || return
  done
  pids=$(pgrep -f "$pattern" 2>/dev/null | tr '\n' ' ')
  if [ -n "$pids" ]; then
    log "  forcing remaining $pids"
    # shellcheck disable=SC2086
    kill -9 $pids 2>/dev/null || true
  fi
}

target_attempts() {
  if [ -n "${2:-}" ]; then printf '%s' "$2"
  elif [ -f jobs/v1-target-attempts ]; then tr -d '[:space:]' < jobs/v1-target-attempts
  else printf '1'
  fi
}

case "${1:-status}" in
  status)
    python3 scripts/v1_panel_status.py
    ;;
  pause)
    mkdir -p jobs
    : > "$MARKER"
    log "pause guard created; completed receipts remain untouched"
    stop_pattern "v1 nightly supervisor" 'run_v1_nightly\.sh'
    stop_pattern "v1 provider runners" 'run_v1_panel\.py.*--provider'
    stop_pattern "v1 Harbor processes" 'harbor (run|job resume).*v1-'
    python3 scripts/v1_panel_status.py
    log "Any task container still visible in docker ps should finish or be stopped manually; unrelated containers were not touched."
    ;;
  resume)
    target=$(target_attempts "$@")
    case "$target" in 1|2|3|4|5) ;; *) echo "target attempts must be 1..5" >&2; exit 2 ;; esac
    if pgrep -f 'run_v1_panel\.py.*--provider|run_v1_nightly\.sh' >/dev/null 2>&1; then
      log "ABORT: v1 campaign already running"
      exit 1
    fi
    rm -f "$MARKER"
    printf '%s\n' "$target" > jobs/v1-target-attempts
    log "starting/resuming provider lanes toward k=$target"
    nohup bash scripts/run_v1_nightly.sh "$target" >> jobs/v1-nightly-supervisor.log 2>&1 &
    sleep 3
    python3 scripts/v1_panel_status.py --target-attempts "$target"
    ;;
  *)
    echo "usage: bash scripts/v1_panel_control.sh [status|pause|resume [1-5]]" >&2
    exit 2
    ;;
esac
