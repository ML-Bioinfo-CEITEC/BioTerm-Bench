#!/usr/bin/env python3
"""Summarise one model's run over the whole task suite, split by cohort.

Reports the three metrics the manuscript uses -- mean reward (primary),
pass@1, and all-attempts (a task counts only if *every* attempt passed) --
overall and separately for the 25-task core, the hard extension, and the new
v1.0 candidates, so a claim about the suite is never made from a single pooled
number over cohorts of different difficulty.

Operational filtering matches the rest of the pipeline: a trial with a non-null
`exception_info`, or with no scored reward, is an error rather than a failure
and is excluded from the score while still being counted and reported.

Usage:
    python3 scripts/full_bench_report.py jobs/qwen38-27b-full53-k3
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def read_list(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {x.strip() for x in path.read_text().splitlines()
            if x.strip() and not x.startswith("#")}


def cohorts(root: Path) -> dict[str, set[str]]:
    retired = read_list(root / "configs/retired_tasks.txt")
    core = read_list(root / "configs/core25_tasks.txt") - retired
    hard = read_list(root / "configs/v2_retained_tasks.txt") - retired
    new = (read_list(root / "configs/v10_candidates.txt")
           | read_list(root / "configs/v10_round2_tasks.txt"))
    return {"core-25": core, "hard extension": hard, "v1.0 candidates": new}


def metrics(scores: dict[str, list[float]]) -> tuple[float, float, float, int, int]:
    trials = [v for vals in scores.values() for v in vals]
    if not trials:
        return 0.0, 0.0, 0.0, 0, 0
    mean = sum(trials) / len(trials)
    pass1 = sum(1 for vals in scores.values() if any(v >= 1.0 for v in vals)) / len(scores)
    allatt = sum(1 for vals in scores.values() if all(v >= 1.0 for v in vals)) / len(scores)
    return mean, pass1, allatt, len(scores), len(trials)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("job", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--show-tasks", action="store_true")
    args = parser.parse_args()

    scores: dict[str, list[float]] = defaultdict(list)
    errors: dict[str, int] = defaultdict(int)
    for result in sorted(args.job.glob("*/result.json")):
        data = json.loads(result.read_text())
        task = data["task_name"]
        reward = ((data.get("verifier_result") or {}).get("rewards") or {}).get("reward")
        if data.get("exception_info") or reward is None:
            errors[task] += 1
            continue
        scores[task].append(float(reward))

    if not scores:
        print("no scored trials yet")
        return 0

    groups = cohorts(args.root)
    assigned = set().union(*groups.values())
    groups["unclassified"] = set(scores) - assigned

    print(f"{args.job.name}\n")
    print(f"{'cohort':<18}{'tasks':>7}{'trials':>8}{'mean':>8}{'pass@1':>9}{'all-att':>9}")
    print("-" * 59)
    for label, members in groups.items():
        sub = {t: v for t, v in scores.items() if t in members}
        if not sub:
            continue
        mean, p1, aa, n_task, n_trial = metrics(sub)
        print(f"{label:<18}{n_task:>7}{n_trial:>8}{mean:>8.3f}{p1:>9.3f}{aa:>9.3f}")
    mean, p1, aa, n_task, n_trial = metrics(scores)
    print("-" * 59)
    print(f"{'ALL':<18}{n_task:>7}{n_trial:>8}{mean:>8.3f}{p1:>9.3f}{aa:>9.3f}")

    n_err = sum(errors.values())
    if n_err:
        rate = n_err / (n_trial + n_err)
        print(f"\n{n_err} errored trials ({rate:.1%}) excluded from the scores above")
        for t, c in sorted(errors.items(), key=lambda kv: -kv[1])[:8]:
            print(f"    {t}: {c}")

    failing = {t: v for t, v in scores.items() if not all(x >= 1.0 for x in v)}
    print(f"\n{len(failing)} of {len(scores)} tasks were not solved on every attempt:")
    for t in sorted(failing, key=lambda t: sum(scores[t]) / len(scores[t])):
        v = scores[t]
        print(f"    {sum(1 for x in v if x >= 1.0)}/{len(v)}  {t}")

    if args.show_tasks:
        print("\nper-task mean reward")
        for t in sorted(scores, key=lambda t: (sum(scores[t]) / len(scores[t]), t)):
            v = scores[t]
            print(f"    {sum(v)/len(v):.3f}  {t}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
