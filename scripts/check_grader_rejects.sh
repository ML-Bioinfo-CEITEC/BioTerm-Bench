#!/usr/bin/env bash
# Negative oracle: a grader must REJECT a corrupted answer.
#
# check_oracle.sh proves the grader accepts the reference solution. That alone
# does not prove it grades anything -- a grader that ignores its input passes
# too. This runs the reference solution, perturbs one number in each output
# file, and requires check.py to fail.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

status=0
for name in "$@"; do
  t="tasks/$name"
  [ -d "$t" ] || { echo "  MISSING  $name"; status=1; continue; }
  img=$(grep -o 'docker_image *= *"[^"]*"' "$t/task.toml" | sed 's/.*"\(.*\)"/\1/')
  out=$(docker run --rm \
      -v "$ROOT/$t/data":/app/data:ro \
      -v "$ROOT/$t/solution":/solution:ro \
      -v "$ROOT/$t/tests":/tests:ro \
      "${img:-bioterm-base:v1}" bash -c '
        set -e
        bash /solution/solve.sh > /dev/null 2>&1
        set +e
        python3 - <<PY
import pathlib, re, sys
# Nudge the last numeric field of the first available data row of every text
# output. Binary-only tasks are reported as explicit N/A below.
changed = 0
for p in sorted(pathlib.Path("/app/output").rglob("*")):
    if not p.is_file():
        continue
    try:
        lines = p.read_text().splitlines()
    except UnicodeDecodeError:
        continue
    if len(lines) < 2:
        continue
    row = 1
    f = lines[row].split("\t")
    for i in range(len(f) - 1, -1, -1):
        try:
            f[i] = str(float(f[i]) * 1.5 + 7.0)
        except ValueError:
            continue
        changed += 1
        break
    else:
        f[-1] = f[-1] + "_X"
        changed += 1
    lines[row] = "\t".join(f)
    p.write_text("\n".join(lines) + "\n")
sys.exit(0 if changed else 3)
PY
        mutate_rc=$?
        set -e
        if [ "$mutate_rc" -eq 3 ]; then
            echo NO_MUTABLE_TEXT_OUTPUT
            exit 0
        fi
        if python3 /tests/check.py > /dev/null 2>&1; then
            echo ACCEPTED_CORRUPT
        else
            echo REJECTED
        fi' 2>&1 | tail -1)
  case "$out" in
    REJECTED)         printf "  ok       %s\n" "$name" ;;
    NO_MUTABLE_TEXT_OUTPUT) printf "  n/a      %s (binary or single-record output)\n" "$name" ;;
    ACCEPTED_CORRUPT) printf "  FAIL     %s -- grader accepted a corrupted answer\n" "$name"; status=1 ;;
    *)                printf "  ERROR    %s -- %s\n" "$name" "$out"; status=1 ;;
  esac
done
exit $status
