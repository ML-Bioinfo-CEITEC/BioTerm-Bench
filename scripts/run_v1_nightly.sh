#!/usr/bin/env bash
# Run one e-INFRA lane and one OpenRouter lane concurrently; local is optional.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

target="${1:-1}"
case "$target" in 1|2|3|4|5) ;; *) echo "target attempts must be 1..5" >&2; exit 2 ;; esac
mkdir -p jobs
printf '%s\n' "$target" > jobs/v1-target-attempts

if [ -f jobs/.v1-panel-paused ]; then
  echo "v1 campaign is paused; resume with: bash scripts/v1_panel_control.sh resume $target" >&2
  exit 1
fi

python3 scripts/freeze_benchmark_v1.py --verify
python3 scripts/sync_v1_model_panel.py

if ! pgrep -f 'docker_network_janitor\.sh' >/dev/null 2>&1; then
  bash scripts/docker_network_janitor.sh >> jobs/docker-network-janitor.log 2>&1 &
fi

python3 scripts/run_v1_panel.py --provider einfra --target-attempts "$target" \
  >> jobs/v1-einfra-runner.log 2>&1 &
einfra_pid=$!
python3 scripts/run_v1_panel.py --provider openrouter --target-attempts "$target" \
  >> jobs/v1-openrouter-runner.log 2>&1 &
openrouter_pid=$!

local_pid=""
if awk -F '\t' 'NR > 1 && $2 == "local" { found=1 } END { exit !found }' configs/v1_model_panel.tsv; then
  python3 scripts/run_v1_panel.py --provider local --target-attempts "$target" \
    >> jobs/v1-local-runner.log 2>&1 &
  local_pid=$!
fi

wait "$einfra_pid" || true
wait "$openrouter_pid" || true
if [ -n "$local_pid" ]; then wait "$local_pid" || true; fi
python3 scripts/v1_panel_status.py --target-attempts "$target"
