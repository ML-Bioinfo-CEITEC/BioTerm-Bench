#!/usr/bin/env bash
# Compact k=4 OpenRouter sweep: 25 tasks x 4 attempts = 100 trials/model.
#
# Default manifest is tuned for an ~8 hour open-weight / open-available run.
# Use INCLUDE_OVERFLOW=1 to append the larger optional models.
#
# Examples:
#   bash scripts/run_open_models_k4_8h.sh
#   ONLY_MODELS=gpt-oss-20b bash scripts/run_open_models_k4_8h.sh
#   START_FROM=qwen3-14b bash scripts/run_open_models_k4_8h.sh
#   INCLUDE_OVERFLOW=1 bash scripts/run_open_models_k4_8h.sh
#   VALIDATE_ONLY=1 bash scripts/run_open_models_k4_8h.sh
#
# Requires: bioterm-*:v1 images, OPENROUTER_API_KEY, and harbor on PATH.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p jobs

TASKS_PATH="${TASKS_PATH:-tasks/}"
MANIFEST="${MANIFEST:-configs/k4_open_8h_models.tsv}"
MASTER="${MASTER:-jobs/k4-open-8h-master.log}"
SKIP_COMPLETED="${SKIP_COMPLETED:-1}"
INCLUDE_OVERFLOW="${INCLUDE_OVERFLOW:-0}"
ONLY_MODELS="${ONLY_MODELS:-}"
START_FROM="${START_FROM:-}"
VALIDATE_ONLY="${VALIDATE_ONLY:-0}"

if [[ ! -f "$MANIFEST" ]]; then
  echo "ERROR: manifest not found: $MANIFEST" >&2
  exit 1
fi

has_slug() {
  local needle="$1"
  local csv="$2"
  [[ ",${csv}," == *",${needle},"* ]]
}

validate_manifest() {
  python3 - "$MANIFEST" <<'PY'
import csv
import json
import sys
import urllib.request

manifest = sys.argv[1]
with open(manifest, newline="") as fh:
    rows = list(csv.DictReader(fh, delimiter="\t"))

ids = [row["model_id"].removeprefix("openrouter/") for row in rows]
try:
    with urllib.request.urlopen("https://openrouter.ai/api/v1/models", timeout=30) as resp:
        data = json.load(resp)
except Exception as exc:
    print(f"WARN: could not fetch OpenRouter model list: {exc}", file=sys.stderr)
    print("WARN: continuing without remote validation", file=sys.stderr)
    sys.exit(0)

available = {item.get("id") for item in data.get("data", [])}
missing = [model_id for model_id in ids if model_id not in available]
if missing:
    print("ERROR: these manifest model IDs were not found on OpenRouter:", file=sys.stderr)
    for model_id in missing:
        print(f"  - {model_id}", file=sys.stderr)
    sys.exit(1)

print(f"Validated {len(ids)} manifest model IDs against OpenRouter.")
PY
}

if [[ "$VALIDATE_ONLY" == "1" ]]; then
  validate_manifest
  exit 0
fi

validate_manifest

echo "=== k4 open 8h sweep start $(date -Iseconds) tasks_path=${TASKS_PATH} manifest=${MANIFEST} ===" | tee "$MASTER"

start_seen=0
if [[ -z "$START_FROM" ]]; then
  start_seen=1
fi

while IFS=$'\t' read -r slug model_id provider_family size_bucket release_hint notes; do
  if [[ "$slug" == "slug" || -z "$slug" ]]; then
    continue
  fi
  if [[ "$notes" == "overflow" && "$INCLUDE_OVERFLOW" != "1" ]]; then
    continue
  fi
  if [[ -n "$ONLY_MODELS" ]] && ! has_slug "$slug" "$ONLY_MODELS"; then
    continue
  fi
  if [[ "$start_seen" == "0" ]]; then
    if [[ "$slug" == "$START_FROM" ]]; then
      start_seen=1
    else
      continue
    fi
  fi

  job_name="full25-k4-open-${slug}"
  result_path="jobs/${job_name}/result.json"

  if [[ -f "$result_path" ]]; then
    status="$(python3 - "$result_path" <<'PY'
import json
import sys
path = sys.argv[1]
with open(path) as fh:
    data = json.load(fh)
finished = data.get("finished_at") is not None
n_total = data.get("n_total_trials")
n_trials = 0
for ev in (data.get("stats") or {}).get("evals", {}).values():
    n_trials = ev.get("n_trials") or 0
    break
if finished and n_total == 100 and n_trials == 100:
    print("complete")
elif finished:
    print(f"finished_incomplete:{n_trials}/{n_total}")
else:
    print(f"partial:{n_trials}/{n_total}")
PY
)"
    if [[ "$status" == "complete" && "$SKIP_COMPLETED" == "1" ]]; then
      echo "=== SKIP ${job_name} already complete ===" | tee -a "$MASTER"
      continue
    fi
    if [[ "$status" != "complete" ]]; then
      echo "ERROR: ${job_name} has existing non-complete result (${status})." | tee -a "$MASTER" >&2
      echo "Rename or remove jobs/${job_name} before retrying this model." | tee -a "$MASTER" >&2
      exit 1
    fi
  fi

  echo "" | tee -a "$MASTER"
  echo "=== START ${job_name} model=${model_id} $(date -Iseconds) ===" | tee -a "$MASTER"
  set +e
  harbor run --path "${TASKS_PATH}" \
    --agent terminus-2 \
    -m "${model_id}" \
    --no-delete -n 2 -k 4 \
    --timeout-multiplier 1.5 \
    --job-name "${job_name}" \
    2>&1 | tee "jobs/${job_name}.log"
  st=$?
  set -e
  echo "=== END ${job_name} exit=${st} $(date -Iseconds) ===" | tee -a "$MASTER"
  if [[ $st -ne 0 ]]; then
    echo "WARN: harbor exit ${st} for ${job_name}; continuing with next model." | tee -a "$MASTER"
  fi
done < "$MANIFEST"

echo "" | tee -a "$MASTER"
echo "=== k4 open 8h sweep complete $(date -Iseconds) ===" | tee -a "$MASTER"
