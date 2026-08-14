#!/usr/bin/env bash
#
# Safely stop all BioTerm-Bench background work so the laptop can be closed.
#
# Nothing is deleted. Partial Harbor jobs are left on disk exactly as they are;
# `resume_experiments.sh` restarts the panel with --skip-completed, which
# resumes a partial job rather than restarting it, so completed trials are kept.
# A trial that is mid-flight when this runs is lost and re-run on resume -- the
# same thing that happened to mistral-medium-3.5 earlier, which then finished
# 100/100 with zero errors.
#
# Order matters: waiters die first, or they would relaunch the panel we are
# about to stop.
#
# Usage:
#   bash scripts/pause_experiments.sh            # stop everything
#   DRY_RUN=1 bash scripts/pause_experiments.sh  # show what would be stopped

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

# Bare pgrep, never `ps | grep -q`: under `set -o pipefail` grep -q exits early,
# ps dies of SIGPIPE, and the pipeline reports "nothing running" when something
# very much is.
stop_matching() {
  local label="$1" pattern="$2" pids
  pids=$(pgrep -f "$pattern" 2>/dev/null | tr '\n' ' ')
  if [ -z "$pids" ]; then
    log "  ${label}: none running"
    return 0
  fi
  if [ -n "${DRY_RUN:-}" ]; then
    log "  ${label}: would stop ${pids}"
    return 0
  fi
  log "  ${label}: stopping ${pids}"
  # shellcheck disable=SC2086
  kill $pids 2>/dev/null
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    sleep 2
    pgrep -f "$pattern" >/dev/null 2>&1 || return 0
  done
  pids=$(pgrep -f "$pattern" 2>/dev/null | tr '\n' ' ')
  if [ -n "$pids" ]; then
    log "  ${label}: still alive after TERM, sending KILL to ${pids}"
    # shellcheck disable=SC2086
    kill -9 $pids 2>/dev/null
  fi
}

log "pausing BioTerm-Bench background work"

# 1. Supervisors first, so nothing relaunches behind us.
stop_matching "waiters"        'einfra_continuation_waiter|openrouter_relaunch_waiter'
stop_matching "repair guard"   'einfra_repair_guard\.sh'
stop_matching "network janitor" 'docker_network_janitor\.sh'

# 2. Panel orchestrators.
stop_matching "panel runners"  'run_einfra_panel\.py|run_openrouter_addon_panel\.py'

# 3. Harbor jobs last: they hold the trials.
stop_matching "harbor jobs"    'harbor (run|job resume) '

# 4. Task containers left behind by --no-delete.
if [ -z "${DRY_RUN:-}" ]; then
  running=$(docker ps -q 2>/dev/null | tr '\n' ' ')
  if [ -n "$running" ]; then
    n_running=$(docker ps -q 2>/dev/null | wc -l | tr -d ' ')
    log "  stopping ${n_running} running container(s)"
    # shellcheck disable=SC2086
    docker stop $running >/dev/null 2>&1
  fi
  docker network prune -f --filter until=10m >/dev/null 2>&1
fi

log "state on disk (nothing deleted):"
python3 - <<'PY'
import json, glob
partial = []
for path in sorted(glob.glob('jobs/einfra-core25-k4-*/result.json')
                   + glob.glob('jobs/einfra-k4-*/result.json')
                   + glob.glob('jobs/openrouter-addon-*/result.json')):
    if 'docker-failed' in path or 'errored' in path:
        continue
    data = json.load(open(path))
    stats = data.get('stats', {})
    if not data.get('finished_at'):
        partial.append((path.split('/')[1], stats.get('n_trials', 0), data.get('n_total_trials', 0)))
if partial:
    print('  partial jobs, will RESUME (not restart) on next run:')
    for name, done, total in partial:
        print(f'    {name}: {done}/{total} trials kept')
else:
    print('  no partial jobs')
PY

log "paused. resume with: bash scripts/resume_experiments.sh"
