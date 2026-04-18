#!/usr/bin/env bash
# Scaffold a new BioTerm-Bench task.
#
# Usage:
#   scripts/new_task.sh <task-id> [--image IMG] [--category CAT] [--difficulty D]
#
# Example:
#   scripts/new_task.sh vcf-annotate-snpeff \
#       --image bioterm-variant:v1 --category variant --difficulty medium
#
# The script refuses to overwrite an existing task directory. The
# result is a skeleton that `scripts/validate_task.py` accepts (files
# exist, required TOML keys present) but whose oracle will fail until
# you fill in real logic and data. Use this to jump-start authoring.
set -euo pipefail

TASK_ID=""
IMAGE="bioterm-base:v1"
CATEGORY="metadata"
DIFFICULTY="easy"

usage() { grep '^# ' "$0" | sed 's/^# \{0,1\}//'; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --image)      IMAGE="$2"; shift 2 ;;
        --category)   CATEGORY="$2"; shift 2 ;;
        --difficulty) DIFFICULTY="$2"; shift 2 ;;
        -h|--help)    usage; exit 0 ;;
        *)
            if [[ -z "${TASK_ID}" ]]; then TASK_ID="$1"; shift
            else echo "unknown arg: $1" >&2; exit 2; fi ;;
    esac
done

if [[ -z "${TASK_ID}" ]]; then
    echo "error: task-id is required" >&2
    usage
    exit 2
fi

if [[ ! "${TASK_ID}" =~ ^[a-z][a-z0-9-]+$ ]]; then
    echo "error: task-id must be lowercase, kebab-case, start with a letter: ${TASK_ID}" >&2
    exit 2
fi

DEST="tasks/${TASK_ID}"
if [[ -e "${DEST}" ]]; then
    echo "error: ${DEST} already exists, refusing to overwrite" >&2
    exit 2
fi

mkdir -p "${DEST}"/{solution,tests,data,gold,environment}

# Harbor requires each task to have an environment/ directory with either
# a Dockerfile or docker-compose.yaml. We ship both: a trivial Dockerfile
# that re-uses the prebuilt image, and a compose override that bind-mounts
# the task's data/ and gold/ dirs into the container so Harbor's agent and
# verifier see /app/data and /gold just like the native oracle runner.
cat > "${DEST}/environment/Dockerfile" <<EOF
FROM ${IMAGE}
RUN mkdir -p /app/output
EOF

cat > "${DEST}/environment/docker-compose.yaml" <<'EOF'
services:
  main:
    volumes:
      - ../data:/app/data:ro
      - ../gold:/gold:ro
EOF

cat > "${DEST}/task.toml" <<EOF
version = "1.0"

[metadata]
author_name  = "TODO"
author_email = "todo@example.org"
difficulty   = "${DIFFICULTY}"
category     = "${CATEGORY}"
tags         = ["${CATEGORY}"]

[verifier]
timeout_sec = 60.0

[agent]
timeout_sec = 600.0

[environment]
build_timeout_sec = 600.0
docker_image      = "${IMAGE}"
cpus              = 2
memory            = "4G"
storage           = "5G"
EOF

cat > "${DEST}/instruction.md" <<'EOF'
TODO: describe the input files under /app/data/, exactly which output
files/paths the agent must produce under /app/output/, and the
acceptance criterion. Keep it under 200 words (validate_task.py
enforces this).
EOF

cat > "${DEST}/solution/solve.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

# TODO: canonical reference solution goes here. This script is the
# ``oracle'' that must make tests/check.py emit reward=1.
EOF
chmod +x "${DEST}/solution/solve.sh"

cat > "${DEST}/tests/test.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 /tests/check.py; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
EOF
chmod +x "${DEST}/tests/test.sh"

cat > "${DEST}/tests/check.py" <<'EOF'
#!/usr/bin/env python3
"""Grader for TODO: task-id.

Prints ``ok: ...`` and exits 0 on pass; prints ``FAIL: ...`` to stderr
and exits 1 on fail. Keep the logic deterministic; no LLM judges.
"""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("/app/output/TODO.ext")
GOLD = Path("/gold/TODO.ext")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


if not OUT.is_file():
    fail(f"missing {OUT}")

# TODO: compare OUT against GOLD using one of the patterns from
# docs/grading-patterns.md.

print("ok: TODO")
sys.exit(0)
EOF

# .gitkeep for data/ and gold/ so the dirs survive an empty-initial commit
touch "${DEST}/data/.gitkeep" "${DEST}/gold/.gitkeep"

echo "scaffolded ${DEST}/"
echo
echo "next steps:"
echo "  1. edit ${DEST}/task.toml metadata"
echo "  2. fill in ${DEST}/instruction.md"
echo "  3. write ${DEST}/solution/solve.sh and ${DEST}/tests/check.py"
echo "  4. populate ${DEST}/data/ and ${DEST}/gold/"
echo "  5. python3 scripts/validate_task.py --only ${TASK_ID}"
echo "  6. bash scripts/run_oracle_all.sh --only ${TASK_ID}"
