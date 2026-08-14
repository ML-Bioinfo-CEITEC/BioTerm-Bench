#!/usr/bin/env bash
#
# Regenerate every paper cohort summary, each into its own directory.
#
# The four scopes must never be globbed together: provider (OpenRouter vs
# e-INFRA) and score scope (core-25 vs hard-8) are both confounders, and the
# summarizer rejects a pattern that crosses provider cohorts. Each invocation
# below is therefore explicit about pattern, provider, and scope.
#
# Cohorts that have no completed jobs yet are skipped with a notice rather
# than failing the run, so this is safe to call while panels are still going.
#
# Usage:
#   bash scripts/refresh_paper_tables.sh
#   DRY_RUN=1 bash scripts/refresh_paper_tables.sh

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

HARD_TASKS=$(sed '/^#/d;/^$/d' configs/v2_retained_tasks.txt | wc -l | tr -d ' ')
# Retired tasks keep their trials on disk but leave the scored aggregate.
RETIRED=$(sed '/^#/d;/^$/d' configs/retired_tasks.txt 2>/dev/null || true)
EXCLUDE_ARGS=""
N_RETIRED=0
for task in ${RETIRED}; do
  EXCLUDE_ARGS="${EXCLUDE_ARGS} --exclude-task ${task}"
  N_RETIRED=$((N_RETIRED + 1))
done
# Pass the full task count: summarize_bioterm_v2.py subtracts the retired ones
# from the expected budget itself, and subtracting here too would double-count.
CORE_TASKS=$(sed '/^#/d;/^$/d' configs/core25_tasks.txt | wc -l | tr -d ' ')
ATTEMPTS=4

run_cohort() {
  local name="$1" pattern="$2" provider="$3" scope="$4" n_tasks="$5" out_dir="$6"
  local expected=$((ATTEMPTS * n_tasks))

  if ! compgen -G "jobs/${pattern}" >/dev/null; then
    echo "skip ${name}: no job directories match jobs/${pattern}"
    return 0
  fi

  echo ">>> ${name}: pattern=${pattern} provider=${provider} scope=${scope} expected=${expected}"
  if [ -n "${DRY_RUN:-}" ]; then
    return 0
  fi
  # shellcheck disable=SC2086
  python3 scripts/summarize_bioterm_v2.py \
    ${EXCLUDE_ARGS} \
    --pattern "${pattern}" \
    --cohort-name "${name}" \
    --expected-trials "${expected}" \
    --attempts-per-task "${ATTEMPTS}" \
    --provider "${provider}" \
    --score-scope "${scope}" \
    --out-dir "${out_dir}" || echo "!!! ${name} failed (rc=$?)"
}

run_cohort openrouter_k4_small 'full25-k4-open-*' openrouter core-25 \
  "${CORE_TASKS}" paper/generated
run_cohort einfra_k4_hard8 'einfra-k4-*' einfra hard-subset \
  "${HARD_TASKS}" paper/generated/einfra-hard8
run_cohort einfra_k4_core25 'einfra-core25-k4-*' einfra core-25 \
  "${CORE_TASKS}" paper/generated/einfra-core25
run_cohort openrouter_addon_hard8 'openrouter-addon-hard8-k4-*' openrouter hard-subset \
  "${HARD_TASKS}" paper/generated/openrouter-addon-hard8
run_cohort openrouter_addon_core25 'openrouter-addon-core25-k4-*' openrouter core-25 \
  "${CORE_TASKS}" paper/generated/openrouter-addon-core25

echo
echo ">>> hardware tiers"
if [ -z "${DRY_RUN:-}" ]; then
  python3 scripts/hardware_tiers.py >/dev/null && echo "wrote hardware tier table and figure"
fi

echo
echo ">>> paired core-25 vs hard-8 comparison"
if [ -z "${DRY_RUN:-}" ]; then
  python3 scripts/paired_scope_table.py || echo "(no paired models yet)"
fi

echo
echo ">>> failure-mode taxonomy (included core-25 OpenRouter jobs)"
if [ -z "${DRY_RUN:-}" ]; then
  included=$(python3 -c "
import csv, pathlib
path = pathlib.Path('paper/generated/openrouter_k4_small_models.csv')
if path.exists():
    rows = [r for r in csv.DictReader(path.open()) if r['status'] == 'included']
    print(' '.join('jobs/' + r['job_name'] for r in rows))
")
  if [ -n "${included}" ]; then
    # shellcheck disable=SC2086
    python3 scripts/summarize_failure_modes.py ${included} \
      --csv paper/generated/failure_modes_openrouter_k4.csv
  else
    echo "skip: no included jobs recorded yet"
  fi
fi
