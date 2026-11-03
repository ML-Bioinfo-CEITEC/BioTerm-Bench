#!/usr/bin/env bash
# Run one task's oracle solution and its grader, the way Harbor would, without
# the agent. A candidate task is not usable until this prints PASS.
#
#   bash scripts/check_oracle.sh <task-name> [<task-name> ...]
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

status=0
for name in "$@"; do
  d="tasks/$name"
  if [ ! -d "$d" ]; then echo "  MISSING  $name"; status=1; continue; fi
  img=$(grep -oE 'docker_image *= *"[^"]+"' "$d/task.toml" | grep -oE '"[^"]+"' | tr -d '"')
  out=$(docker run --rm \
      -v "$PWD/$d/data":/app/data:ro \
      -v "$PWD/$d/solution":/solution:ro \
      -v "$PWD/$d/tests":/tests:ro \
      "$img" bash -c 'mkdir -p /app/output && bash /solution/solve.sh >/tmp/solve.log 2>&1 && python3 /tests/check.py' 2>&1)
  rc=$?
  if [ $rc -eq 0 ]; then
    echo "  PASS     $name"
  else
    echo "  FAIL     $name"
    echo "$out" | tail -4 | sed 's/^/             /'
    status=1
  fi
done
exit $status
