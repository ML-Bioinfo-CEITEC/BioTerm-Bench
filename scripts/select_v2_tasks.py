#!/usr/bin/env python3
"""Select informative v2 tasks from completed development-model probes."""

from __future__ import annotations

import argparse
import json
import tomllib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Attempt:
    task: str
    reward: float | None
    error_type: str | None


def latex_escape(value: str) -> str:
    return value.replace("_", "\\_").replace("&", "\\&").replace("%", "\\%")


def require_candidate_count(candidates: list[str], expected: int = 12) -> None:
    if len(candidates) != expected:
        raise RuntimeError(f"Expected exactly {expected} candidate tasks, found {len(candidates)}")


def require_probe_shape(
    probes: list[list[Attempt]],
    candidates: list[str],
    *,
    expected_models: int = 3,
    attempts_per_model: int = 2,
) -> None:
    if len(probes) != expected_models:
        raise RuntimeError(f"Expected exactly {expected_models} development-model jobs")
    for model_index, attempts in enumerate(probes, start=1):
        counts: dict[str, int] = defaultdict(int)
        for attempt in attempts:
            counts[attempt.task] += 1
        malformed = {
            task: counts.get(task, 0)
            for task in candidates
            if counts.get(task, 0) != attempts_per_model
        }
        unexpected = sorted(set(counts) - set(candidates))
        if malformed or unexpected:
            raise RuntimeError(
                f"Development-model job {model_index} has invalid attempt shape: "
                f"malformed={malformed}, unexpected={unexpected}"
            )


def read_attempts(job_dir: Path) -> list[Attempt]:
    attempts: list[Attempt] = []
    for result_path in sorted(job_dir.glob("*/result.json")):
        data = json.loads(result_path.read_text())
        error = data.get("exception_info") or {}
        rewards = (data.get("verifier_result") or {}).get("rewards") or {}
        reward = rewards.get("reward")
        attempts.append(
            Attempt(
                task=str(data.get("task_name") or ""),
                reward=float(reward) if reward is not None else None,
                error_type=str(error.get("exception_type") or error.get("type") or "") or None,
            )
        )
    return attempts


def select(
    attempts: list[Attempt],
    candidates: list[str],
    *,
    minimum: float,
    maximum: float,
    max_tasks: int = 8,
    expected_attempts_per_task: int | None = None,
    category_by_task: dict[str, str] | None = None,
) -> tuple[list[str], list[dict[str, object]]]:
    by_task: dict[str, list[Attempt]] = defaultdict(list)
    for attempt in attempts:
        if attempt.task:
            by_task[attempt.task].append(attempt)

    receipt: list[dict[str, object]] = []
    for task in candidates:
        task_attempts = by_task.get(task, [])
        scored = [a.reward for a in task_attempts if a.reward is not None and not a.error_type]
        passes = sum(value >= 1.0 for value in scored)
        failures = sum(value < 1.0 for value in scored)
        errors = len(task_attempts) - len(scored)
        rate = passes / len(scored) if scored else None
        complete = (
            expected_attempts_per_task is None or len(task_attempts) == expected_attempts_per_task
        )
        keep = bool(
            complete and passes and failures and rate is not None and minimum <= rate <= maximum
        )
        receipt.append(
            {
                "task": task,
                "category": (category_by_task or {}).get(task, "unknown"),
                "scored_attempts": len(scored),
                "passes": passes,
                "failures": failures,
                "errors": errors,
                "attempts_complete": complete,
                "pass_rate": rate,
                "eligible": keep,
                "retained": False,
            }
        )
    eligible = [row for row in receipt if row["eligible"]]
    eligible.sort(key=lambda row: (abs(float(row["pass_rate"]) - 0.5), str(row["task"])))

    chosen: list[dict[str, object]] = []
    categories = category_by_task or {}
    for category in sorted({categories.get(str(row["task"]), "unknown") for row in eligible}):
        best = next(
            (row for row in eligible if categories.get(str(row["task"]), "unknown") == category),
            None,
        )
        if best is not None and len(chosen) < max_tasks:
            chosen.append(best)
    for row in eligible:
        if row not in chosen and len(chosen) < max_tasks:
            chosen.append(row)

    retained_set = {str(row["task"]) for row in chosen}
    for row in receipt:
        row["retained"] = str(row["task"]) in retained_set
    retained = [task for task in candidates if task in retained_set]
    return retained, receipt


def render_selection_table(path: Path, receipt: list[dict[str, object]]) -> None:
    lines = [
        "\\begin{tabular}{p{0.42\\linewidth}lrrr}",
        "\\toprule",
        "Task & Category & Pass/scored & Pass rate & Errors \\\\",
        "\\midrule",
    ]
    for row in receipt:
        if not row["retained"]:
            continue
        lines.append(
            f"{latex_escape(str(row['task']))} & {latex_escape(str(row['category']))} "
            f"& {row['passes']}/{row['scored_attempts']} & {float(row['pass_rate']):.2f} "
            f"& {row['errors']} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("job_dirs", nargs="+", type=Path)
    parser.add_argument("--candidates", type=Path, default=Path("configs/v2_candidate_tasks.txt"))
    parser.add_argument("--output", type=Path, default=Path("configs/v2_retained_tasks.txt"))
    parser.add_argument("--receipt", type=Path, default=Path("notes/v2_task_selection.json"))
    parser.add_argument(
        "--table", type=Path, default=Path("paper/generated/table_v2_selection.tex")
    )
    parser.add_argument("--minimum-pass-rate", type=float, default=0.10)
    parser.add_argument("--maximum-pass-rate", type=float, default=0.80)
    parser.add_argument("--max-tasks", type=int, default=8)
    parser.add_argument("--expected-attempts-per-task", type=int, default=6)
    args = parser.parse_args()

    candidates = [
        line.strip()
        for line in args.candidates.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    require_candidate_count(candidates)
    probes = [read_attempts(job) for job in args.job_dirs]
    require_probe_shape(probes, candidates)
    attempts = [attempt for probe in probes for attempt in probe]
    category_by_task: dict[str, str] = {}
    for task in candidates:
        task_toml = Path("tasks") / task / "task.toml"
        if task_toml.exists():
            category_by_task[task] = str(
                (tomllib.loads(task_toml.read_text()).get("metadata") or {}).get("category")
                or "unknown"
            )
    retained, receipt = select(
        attempts,
        candidates,
        minimum=args.minimum_pass_rate,
        maximum=args.maximum_pass_rate,
        max_tasks=args.max_tasks,
        expected_attempts_per_task=args.expected_attempts_per_task,
        category_by_task=category_by_task,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(f"{task}\n" for task in retained))
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    render_selection_table(args.table, receipt)
    print(f"retained {len(retained)}/{len(candidates)} tasks")
    for row in receipt:
        rate = row["pass_rate"]
        shown = "NA" if rate is None else f"{rate:.3f}"
        print(f"{row['task']}: pass_rate={shown} errors={row['errors']} retained={row['retained']}")
    all_complete = all(bool(row["attempts_complete"]) for row in receipt)
    return 0 if all_complete and 6 <= len(retained) <= args.max_tasks else 2


if __name__ == "__main__":
    raise SystemExit(main())
