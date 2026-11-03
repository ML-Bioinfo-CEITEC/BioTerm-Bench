#!/usr/bin/env bash
# Keep the two hard-candidate screening lanes alive.
#
# A lane that exits before writing its "finished" marker died to something
# external -- a killed process, an OOM, a provider fault the lane's own retry
# budget did not cover. Harbor resumes rather than restarts, so relaunching is
# cheap and never repeats completed trials.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
LOG="jobs/hardsearch-watchdog.log"

say() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" >> "$LOG"; }

check_lane() {
  local lane="$1" out="jobs/hardsearch-$1.out"
  # pgrep bare: under `pipefail` a `| grep -q` that exits early inverts the
  # status via SIGPIPE, which has already caused one duplicate-panel incident.
  if pgrep -f "run_hardsearch_screen.sh $lane" > /dev/null; then
    return 0
  fi
  if grep -q "lane $lane finished" "$out" 2>/dev/null; then
    return 0
  fi
  say "lane $lane is not running and never finished -- restarting"
  nohup bash scripts/run_hardsearch_screen.sh "$lane" >> "$out" 2>&1 &
  say "lane $lane restarted as pid $!"
}

say "watchdog started (pid $$)"
while true; do
  # Stop once both lanes have written their finished marker.
  if grep -q "lane einfra finished" jobs/hardsearch-einfra.out 2>/dev/null \
     && grep -q "lane openrouter finished" jobs/hardsearch-openrouter.out 2>/dev/null; then
    say "both lanes finished -- watchdog exiting"
    exit 0
  fi
  check_lane einfra
  check_lane openrouter
  if ! pgrep -f docker_network_janitor.sh > /dev/null; then
    say "network janitor died -- restarting"
    nohup bash scripts/docker_network_janitor.sh >> jobs/hardsearch-janitor.log 2>&1 &
  fi
  sleep 300
done
