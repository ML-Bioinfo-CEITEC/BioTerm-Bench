#!/usr/bin/env bash
# Run every task's oracle solution and confirm the grader awards reward=1.
#
# For each tasks/<task-id>/:
#   1. Read the docker image from task.toml ([environment] docker_image)
#   2. docker run the image, mounting solution/, tests/, data/, gold/, and
#      a writable /app/output and /logs
#   3. Execute solution/solve.sh, then tests/test.sh
#   4. Assert /logs/verifier/reward.txt == 1
#
# Exits non-zero if any task fails. This is the gate before release.
#
# Usage:
#   scripts/run_oracle_all.sh
#   scripts/run_oracle_all.sh --only bam-sort-index
#   scripts/run_oracle_all.sh --tasks-dir tasks
#   scripts/run_oracle_all.sh --skip-missing-images
set -euo pipefail

TASKS_DIR="tasks"
ONLY=""
SKIP_MISSING=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tasks-dir)           TASKS_DIR="$2"; shift 2 ;;
        --only)                ONLY="$2";      shift 2 ;;
        --skip-missing-images) SKIP_MISSING=1; shift ;;
        -h|--help)
            grep '^# ' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

if [[ ! -d "${TASKS_DIR}" ]]; then
    echo "tasks dir does not exist: ${TASKS_DIR}" >&2
    exit 2
fi

shopt -s nullglob
task_dirs=("${TASKS_DIR}"/*/)
if [[ ${#task_dirs[@]} -eq 0 ]]; then
    echo "no tasks found under ${TASKS_DIR}/ (nothing to run)"
    exit 0
fi

# Extract ``docker_image = "..."`` from a task.toml. Tolerates either
# single or double quotes; does not require a TOML parser.
extract_image() {
    local toml="$1"
    grep -E '^[[:space:]]*docker_image[[:space:]]*=' "${toml}" \
        | head -1 \
        | sed -E 's/.*=[[:space:]]*"([^"]+)".*/\1/;s/.*=[[:space:]]*'"'"'([^'"'"']+)'"'"'.*/\1/'
}

failures=0
checked=0

for dir in "${task_dirs[@]}"; do
    name="$(basename "${dir%/}")"
    if [[ -n "${ONLY}" && "${name}" != "${ONLY}" ]]; then
        continue
    fi
    checked=$((checked + 1))

    toml="${dir}task.toml"
    if [[ ! -f "${toml}" ]]; then
        echo "FAIL ${name}: missing task.toml"
        failures=$((failures + 1))
        continue
    fi

    image="$(extract_image "${toml}")"
    if [[ -z "${image}" ]]; then
        echo "FAIL ${name}: could not parse docker_image from task.toml"
        failures=$((failures + 1))
        continue
    fi

    echo ">>> ${name} (image: ${image})"

    if ! docker image inspect "${image}" >/dev/null 2>&1; then
        if [[ "${SKIP_MISSING}" -eq 1 ]]; then
            echo "skip ${name}: image ${image} not loaded locally (--skip-missing-images)"
            checked=$((checked - 1))
            continue
        fi
        echo "FAIL ${name}: image ${image} not loaded (docker image inspect failed)"
        failures=$((failures + 1))
        continue
    fi

    logs_dir="$(mktemp -d -t bioterm-oracle-XXXXXX)"
    output_dir="$(mktemp -d -t bioterm-output-XXXXXX)"
    trap 'rm -rf "${logs_dir}" "${output_dir}"' RETURN

    # Mount read-only what the agent would normally see; mount writable
    # what the oracle/grader need to produce artefacts.
    set +e
    docker run --rm \
        -v "$(cd "${dir}" && pwd)/solution:/solution:ro" \
        -v "$(cd "${dir}" && pwd)/tests:/tests:ro" \
        -v "$(cd "${dir}" && pwd)/data:/app/data:ro" \
        -v "$(cd "${dir}" && pwd)/gold:/gold:ro" \
        -v "${output_dir}:/app/output" \
        -v "${logs_dir}:/logs" \
        -e NCBI_API_KEY="${NCBI_API_KEY:-}" \
        -e BIOTERM_OFFLINE="${BIOTERM_OFFLINE:-}" \
        "${image}" \
        bash -c 'trap "chmod -R a+rwX /logs /app/output" EXIT; set -e; mkdir -p /logs/verifier; bash /solution/solve.sh; bash /tests/test.sh'
    rc=$?
    set -e

    reward_file="${logs_dir}/verifier/reward.txt"
    reward="$( [[ -f "${reward_file}" ]] && cat "${reward_file}" || echo "<missing>")"

    if [[ "${rc}" -ne 0 || "${reward}" != "1" ]]; then
        echo "FAIL ${name}: exit=${rc} reward=${reward}"
        failures=$((failures + 1))
    else
        echo "ok   ${name}"
    fi

    rm -rf "${logs_dir}" "${output_dir}"
    trap - RETURN
done

echo
echo "${checked} tasks checked, ${failures} failed"
exit $(( failures > 0 ? 1 : 0 ))
