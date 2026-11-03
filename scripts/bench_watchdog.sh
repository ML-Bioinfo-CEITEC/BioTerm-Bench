#!/usr/bin/env bash
# Keep the round-2 lanes and the network janitor alive.
#
# A lane writes "lane <suffix> finished" as its last act, so a lane that is
# neither running nor finished died to something external and is relaunched.
# Harbor resumes, so a relaunch never repeats a scored trial.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
LOG=jobs/bench-watchdog.log
say() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" >> "$LOG"; }

say "watchdog started (pid $$)"
while true; do
  if ! pgrep -f docker_network_janitor.sh > /dev/null; then
    say "network janitor died -- restarting"
    nohup bash scripts/docker_network_janitor.sh >> jobs/hardsearch-janitor.log 2>&1 &
  fi
  # Each round is a single orchestrator holding its lanes. If one is gone and
  # its final lane never reported finished, bring the orchestrator back.
  revive() {
    local script="$1" outfile="$2" marker="$3"
    if pgrep -f "$script" > /dev/null; then return 0; fi
    if grep -q "$marker" "$outfile" 2>/dev/null; then return 0; fi
    say "$script is gone and '$marker' never appeared -- relaunching"
    nohup bash "scripts/$script" >> "jobs/${script%.sh}.out" 2>&1 &
    return 1
  }

  all_done=1
  revive hardsearch_round2.sh jobs/lane-full53.out "lane qwen38-27b-full53-k3 finished" || all_done=0
  revive hardsearch_round2.sh jobs/lane-round2-einfra.out "lane hardsearch2-k3-gpt-oss-120b finished" || all_done=0
  revive hardsearch_round3.sh jobs/lane-round3-openrouter.out "lane hardsearch3-k3-qwen38-27b finished" || all_done=0
  revive hardsearch_round3.sh jobs/lane-round3-einfra.out "lane hardsearch3-k3-gpt-oss-120b finished" || all_done=0
  revive hardsearch_round4.sh jobs/lane-round4-einfra.out "lane hardsearch4-k3-gpt-oss-120b finished" || all_done=0
  revive hardsearch_round4.sh jobs/lane-round4-openrouter.out "lane hardsearch4-k3-qwen38-27b finished" || all_done=0
  revive hardsearch_round5.sh jobs/lane-round5-einfra.out "lane hardsearch5-k3-gpt-oss-120b finished" || all_done=0
  revive hardsearch_round5.sh jobs/lane-round5-openrouter.out "lane hardsearch5-k3-qwen38-27b finished" || all_done=0
  revive hardsearch_round6.sh jobs/lane-round6-einfra.out "lane hardsearch6-k3-gpt-oss-120b finished" || all_done=0
  revive hardsearch_round6.sh jobs/lane-round6-openrouter.out "lane hardsearch6-k3-qwen38-27b finished" || all_done=0
  if [ "$all_done" = 1 ] \
     && ! pgrep -f hardsearch_round2.sh > /dev/null \
     && ! pgrep -f hardsearch_round3.sh > /dev/null \
     && ! pgrep -f hardsearch_round4.sh > /dev/null \
     && ! pgrep -f hardsearch_round5.sh > /dev/null \
     && ! pgrep -f hardsearch_round6.sh > /dev/null; then
    say "all rounds finished -- watchdog exiting"
    exit 0
  fi

  sleep 300
done
