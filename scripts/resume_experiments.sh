#!/usr/bin/env bash
#
# Restart BioTerm-Bench background work after pause_experiments.sh.
#
# Only the e-INFRA lane has work left; the OpenRouter add-on panel finished all
# 15 of its jobs on 2026-08-13. The waiter runs the core-25 sweep with
# --skip-completed, which skips finished models and RESUMES partial jobs, so
# nothing already computed is recomputed.
#
# Requires E_INFRA_API_KEY in the gitignored .env; it is mapped to
# EINFRA_AI_TOKEN inside the child process only and never printed.
#
# Usage:
#   bash scripts/resume_experiments.sh
#   bash scripts/resume_experiments.sh --status   # just report, start nothing

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

already_running() {
  pgrep -f 'einfra_continuation_waiter|run_einfra_panel\.py|harbor (run|job resume) ' >/dev/null 2>&1
}

report() {
  python3 - <<'PY'
import json, glob
rows = []
for path in sorted(glob.glob('jobs/einfra-core25-k4-*/result.json')):
    if 'docker-failed' in path:
        continue
    data = json.load(open(path))
    stats = data.get('stats', {})
    rows.append((path.split('/')[1], stats.get('n_trials', 0), bool(data.get('finished_at'))))
done = sum(1 for r in rows if r[2])
print(f'  e-INFRA core-25: {done}/9 models complete')
for name, trials, finished in rows:
    print(f"    {'DONE' if finished else 'PART'} {name}: {trials}/100")
PY
}

if [ "${1:-}" = "--status" ]; then
  report
  already_running && log "background work IS running" || log "background work is stopped"
  exit 0
fi

if already_running; then
  log "ABORT: e-INFRA work is already running; nothing to do"
  report
  exit 1
fi

if [ ! -f .env ]; then
  log "ABORT: .env missing (needs E_INFRA_API_KEY)"
  exit 1
fi

log "current state before resuming:"
report

log "starting Docker network janitor"
nohup bash jobs/docker_network_janitor.sh >> jobs/docker-network-janitor.log 2>&1 &
disown

log "starting e-INFRA waiter (core-25 sweep, resumes partial jobs)"
nohup bash jobs/einfra_continuation_waiter_v2.sh >> jobs/einfra-hard8-continuation.log 2>&1 &
disown

log "starting post-sweep supervisor (kimi-k3 hard-8 re-run, then Docker repairs)"
nohup bash jobs/einfra_post_sweep.sh >> jobs/einfra-post-sweep.log 2>&1 &
disown

sleep 5
log "processes now running:"
pgrep -fl 'einfra_continuation_waiter|docker_network_janitor|einfra_post_sweep' | sed 's/^/    /'
log "resumed. watch with: tail -f jobs/einfra-hard8-continuation.log"
