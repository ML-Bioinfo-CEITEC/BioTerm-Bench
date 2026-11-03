#!/usr/bin/env bash
# Third oracle: a grader must ACCEPT a correct answer formatted differently.
#
# check_oracle.sh proves the grader accepts the reference answer byte for byte.
# check_grader_rejects.sh proves it rejects a corrupted one. Neither proves it
# accepts an answer that is *right* but rendered differently, which is the hole
# `fastq-paired-adapter-qc` fell through: its grader compares parsed JSON with
# exact equality against four-decimal gold, while the instruction never asks
# for rounding, so five models failed twelve trials on a correct computation.
#
# The perturbation is deliberately negligible: every numeric field is nudged by
# a relative 1e-9, far below any rounding a task specifies. A grader that
# rejects that is comparing text or floats exactly, and will fail correct work.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

status=0
for name in "$@"; do
  t="tasks/$name"
  [ -d "$t" ] || { echo "  MISSING  $name"; status=1; continue; }
  if grep -Fxq "$name" <(sed '/^#/d;/^$/d' configs/exact_format_tasks.txt); then
    printf "  n/a       %s (contract requires exact formatting)\n" "$name"
    continue
  fi
  img=$(grep -o 'docker_image *= *"[^"]*"' "$t/task.toml" | sed 's/.*"\(.*\)"/\1/')
  mounts=(-v "$ROOT/$t/data":/app/data:ro -v "$ROOT/$t/solution":/solution:ro
          -v "$ROOT/$t/tests":/tests:ro)
  [ -d "$t/gold" ] && mounts+=(-v "$ROOT/$t/gold":/gold:ro)
  out=$(docker run --rm "${mounts[@]}" "${img:-bioterm-base:v1}" bash -c '
    bash /solution/solve.sh > /dev/null 2>&1 || true
    python3 - <<PY
import json, pathlib, re, sys
touched = 0
for p in sorted(pathlib.Path("/app/output").rglob("*")):
    if not p.is_file():
        continue
    try:
        raw = p.read_text()
    except (UnicodeDecodeError, ValueError):
        continue                      # binary deliverable (bgzip, index): skip
    if p.suffix == ".json":
        try:
            obj = json.loads(raw)
        except ValueError:
            continue
        def nudge(o):
            global touched
            if isinstance(o, dict):
                return {k: nudge(v) for k, v in o.items()}
            if isinstance(o, list):
                return [nudge(v) for v in o]
            if isinstance(o, float):
                touched += 1
                return o * (1 + 1e-9)
            return o
        p.write_text(json.dumps(nudge(obj), indent=2, sort_keys=True))
        continue
    lines = raw.splitlines()
    out = []
    for i, line in enumerate(lines):
        if i == 0:
            out.append(line); continue
        fields = line.split("\t")
        for j, f in enumerate(fields):
            if re.fullmatch(r"-?\d+\.\d+", f):
                fields[j] = repr(float(f) * (1 + 1e-9))
                touched += 1
        out.append("\t".join(fields))
    p.write_text("\n".join(out) + "\n")
sys.exit(0 if touched else 3)
PY
    rc=$?
    if [ $rc -eq 3 ]; then echo NO_FLOATS; exit 0; fi
    if python3 /tests/check.py > /dev/null 2>&1; then echo TOLERANT; else echo BRITTLE; fi' 2>&1 | tail -1)
  case "$out" in
    TOLERANT)  printf "  ok        %s\n" "$name" ;;
    NO_FLOATS) printf "  n/a       %s (no float fields to perturb)\n" "$name" ;;
    BRITTLE)   printf "  BRITTLE   %s -- rejects a correct answer differing by 1e-9\n" "$name"; status=1 ;;
    *)         printf "  ERROR     %s -- %s\n" "$name" "$out"; status=1 ;;
  esac
done
exit $status
