#!/usr/bin/env bash
# Reclaim Docker networks left behind by Harbor's --no-delete runs.
#
# --no-delete is required (without it Harbor wipes the prebuilt task images),
# but it also leaves one bridge network per trial. Docker's default address
# pool holds about 31 of them; once it is exhausted every later trial fails to
# start and the running job is destroyed. That has already cost one job 95 of
# its 99 trials.
#
# `docker network prune` only touches networks with no attached container, and
# the `until` filter keeps it off anything created in the last ten minutes, so
# a network whose container has not yet attached is never taken.
set -uo pipefail

INTERVAL="${JANITOR_INTERVAL:-120}"
MIN_AGE="${JANITOR_MIN_AGE:-10m}"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] network janitor started (pid $$, every ${INTERVAL}s, min age ${MIN_AGE})"
while true; do
  before=$(docker network ls -q | wc -l | tr -d ' ')
  if [ "$before" -ge 12 ]; then
    docker network prune -f --filter "until=${MIN_AGE}" > /dev/null 2>&1
    after=$(docker network ls -q | wc -l | tr -d ' ')
    if [ "$before" != "$after" ]; then
      echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] pruned $((before - after)) networks ($before -> $after)"
    fi
  fi
  sleep "$INTERVAL"
done
