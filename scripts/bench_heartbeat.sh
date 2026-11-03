#!/usr/bin/env bash
# Emit one compact status line every 30 minutes, plus an immediate ALERT when
# the machine looks stalled. Stdout is the event stream.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

stalled=0
while true; do
  # Glob every screening round, not just the first two: an under-counting
  # heartbeat reads as a stall when later rounds are the only thing running.
  scored=$(ls jobs/hardsearch*-k*/*/result.json jobs/qwen38-27b-full53-k3/*/result.json \
              2>/dev/null | wc -l | tr -d ' ')
  containers=$(docker ps -q 2>/dev/null | wc -l | tr -d ' ')
  nets=$(docker network ls -q 2>/dev/null | wc -l | tr -d ' ')
  # macOS pgrep has no -c; count lines instead.
  lanes=$(( $(pgrep -f run_bench_lane.sh 2>/dev/null | wc -l) + $(pgrep -f run_hardsearch_screen.sh 2>/dev/null | wc -l) ))
  free=$(df -g / | tail -1 | awk '{print $4}')

  if [ "$containers" = 0 ] && [ "$lanes" != 0 ]; then
    stalled=$((stalled + 1))
  else
    stalled=0
  fi
  if [ "$stalled" -ge 2 ]; then
    echo "ALERT stalled: $lanes lane(s) alive but no container for 10+ min; scored=$scored nets=$nets"
    stalled=0
  fi
  if [ "$lanes" = 0 ] && [ "$containers" = 0 ]; then
    echo "DONE all lanes idle; scored=$scored trials"
    exit 0
  fi
  if [ "$nets" -gt 25 ]; then
    echo "ALERT docker networks at $nets of ~31 -- pool exhaustion is near"
  fi
  if [ "$free" -lt 40 ]; then
    echo "ALERT disk free ${free}GB"
  fi

  echo "$(date -u +%H:%M)Z scored=$scored lanes=$lanes containers=$containers nets=$nets diskGB=$free"
  sleep 1800
done
