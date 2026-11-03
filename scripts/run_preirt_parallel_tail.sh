#!/usr/bin/env bash
# After Qwen3.8 completes, run the two final OpenRouter deployments in parallel.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

while true; do
  if [ -f jobs/.preirt-paused ]; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) parallel tail paused before launch"
    exit 0
  fi
  if python3 - <<'PY'
from pathlib import Path
from scripts.preirt_common import job_scored_complete
raise SystemExit(0 if job_scored_complete(Path("jobs/preirt-k1-or-qwen38-27b"), 113) else 1)
PY
  then
    break
  fi
  sleep 30
done

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) launching Luna and GPT-OSS-120B bridge concurrently"
python3 scripts/run_preirt_panel.py --provider openrouter --phase k1 --only or-gpt56-luna &
luna_pid=$!
python3 scripts/run_preirt_panel.py --provider openrouter --phase k1 --only or-gptoss-120b &
bridge_pid=$!
wait "$luna_pid"
luna_rc=$?
wait "$bridge_pid"
bridge_rc=$?
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) parallel tail finished luna=$luna_rc bridge=$bridge_rc"
exit $((luna_rc || bridge_rc))
