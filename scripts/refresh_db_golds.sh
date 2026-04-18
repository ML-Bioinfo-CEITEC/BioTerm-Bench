#!/usr/bin/env bash
# Regenerate gold sets for DB-retrieval tasks against live upstream APIs.
#
# Identifies DB tasks by the presence of ``network = "restricted"`` and a
# non-empty ``allowed_hosts`` list in task.toml (see docs/live-network-pattern.md).
# For each such task, runs the oracle solution with network access and
# copies the produced outputs into gold/.
#
# Run this at the START of every formal evaluation cycle. Cross-cycle
# scores must be reported with the gold-refresh commit timestamp.
#
# Usage:
#   NCBI_API_KEY=... scripts/refresh_db_golds.sh
#   NCBI_API_KEY=... scripts/refresh_db_golds.sh --only mygene-properties-query
set -euo pipefail

TASKS_DIR="tasks"
ONLY=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tasks-dir) TASKS_DIR="$2"; shift 2 ;;
        --only)      ONLY="$2";      shift 2 ;;
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
    echo "no tasks found under ${TASKS_DIR}/ -- nothing to refresh"
    exit 0
fi

is_db_task() {
    local toml="$1"
    grep -qE '^[[:space:]]*network[[:space:]]*=[[:space:]]*"restricted"' "${toml}"
}

extract_image() {
    local toml="$1"
    grep -E '^[[:space:]]*docker_image[[:space:]]*=' "${toml}" \
        | head -1 \
        | sed -E 's/.*=[[:space:]]*"([^"]+)".*/\1/;s/.*=[[:space:]]*'"'"'([^'"'"']+)'"'"'.*/\1/'
}

refreshed=0

for dir in "${task_dirs[@]}"; do
    name="$(basename "${dir%/}")"
    if [[ -n "${ONLY}" && "${name}" != "${ONLY}" ]]; then
        continue
    fi
    toml="${dir}task.toml"
    [[ -f "${toml}" ]] || continue
    is_db_task "${toml}" || continue

    image="$(extract_image "${toml}")"
    if [[ -z "${image}" ]]; then
        echo "skip ${name}: could not parse docker_image"
        continue
    fi

    echo ">>> refreshing ${name}"

    output_dir="$(mktemp -d -t bioterm-refresh-XXXXXX)"

    docker run --rm \
        -v "$(cd "${dir}" && pwd)/solution:/solution:ro" \
        -v "$(cd "${dir}" && pwd)/data:/app/data:ro" \
        -v "${output_dir}:/app/output" \
        -e NCBI_API_KEY="${NCBI_API_KEY:-}" \
        "${image}" \
        bash -c 'set -e; bash /solution/solve.sh'

    # Replace gold/ wholesale. Authors commit the diff for review.
    rm -rf "${dir}gold"
    mkdir -p "${dir}gold"
    cp -R "${output_dir}/." "${dir}gold/"
    rm -rf "${output_dir}"

    refreshed=$((refreshed + 1))
done

echo
echo "${refreshed} DB gold sets refreshed"
if [[ "${refreshed}" -gt 0 ]]; then
    echo "next steps:"
    echo "  git add ${TASKS_DIR}/*/gold"
    echo "  git commit -m \"refresh: DB gold sets $(date -u +%Y-%m-%d)\""
fi
