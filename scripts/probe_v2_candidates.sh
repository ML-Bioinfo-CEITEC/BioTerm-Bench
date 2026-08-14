#!/usr/bin/env bash
# Probe all v2 candidate tasks with weak/middle/strong development models.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TASK_LIST="${TASK_LIST:-configs/v2_candidate_tasks.txt}"
MODEL_MANIFEST="${MODEL_MANIFEST:-configs/v2_probe_models.tsv}"
JOBS_DIR="${JOBS_DIR:-jobs}"
RUN_TAG="${RUN_TAG:-}"
ONLY_MODELS="${ONLY_MODELS:-}"
START_FROM="${START_FROM:-}"
VALIDATE_ONLY="${VALIDATE_ONLY:-0}"

has_slug() {
  local needle="$1"
  [[ ",${ONLY_MODELS}," == *",${needle},"* ]]
}

tasks=()
while IFS= read -r task; do
  [[ -n "$task" ]] && tasks+=("$task")
done < <(sed '/^[[:space:]]*#/d; /^[[:space:]]*$/d' "$TASK_LIST")
if [[ "${#tasks[@]}" -ne 12 ]]; then
  echo "ERROR: expected 12 candidate tasks in ${TASK_LIST}, found ${#tasks[@]}" >&2
  exit 1
fi

for task in "${tasks[@]}"; do
  python3 scripts/validate_task.py --only "$task"
done

if [[ "$VALIDATE_ONLY" == "1" ]]; then
  exit 0
fi

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  echo "ERROR: OPENROUTER_API_KEY is required" >&2
  exit 1
fi

mkdir -p "$JOBS_DIR"
started=0
[[ -z "$START_FROM" ]] && started=1

while IFS=$'\t' read -r slug model_id role; do
  [[ "$slug" == "slug" || -z "$slug" ]] && continue
  if [[ -n "$ONLY_MODELS" ]] && ! has_slug "$slug"; then
    continue
  fi
  if [[ "$started" == "0" ]]; then
    [[ "$slug" == "$START_FROM" ]] && started=1 || continue
  fi

  if [[ -n "$RUN_TAG" ]]; then
    job="probe-v2-${RUN_TAG}-${slug}-k2"
  else
    job="probe-v2-${slug}-k2"
  fi
  if [[ -f "${JOBS_DIR}/${job}/result.json" ]]; then
    echo "SKIP ${job}: result exists; use harbor job resume for an incomplete job"
    continue
  fi

  args=(
    harbor run --path tasks/ --agent terminus-2 -m "$model_id"
    --no-delete -n 2 -k 2 --timeout-multiplier 1.5
    --job-name "$job" --jobs-dir "$JOBS_DIR"
  )
  for task in "${tasks[@]}"; do
    args+=(--include-task-name "$task")
  done

  echo "START ${job} role=${role}"
  set +e
  "${args[@]}" 2>&1 | tee "${JOBS_DIR}/${job}.log"
  status=${PIPESTATUS[0]}
  set -e
  if [[ "$status" -ne 0 ]]; then
    echo "WARN ${job}: Harbor exit ${status}; resume with: harbor job resume -p ${JOBS_DIR}/${job}" >&2
  fi
done < "$MODEL_MANIFEST"
