#!/usr/bin/env python3
"""Summarize BioTerm-Bench k=4 sweep results.

Default input is jobs/full25-k4-open-*/result.json. The summary uses classic
averages: mean reward over attempts, pass@1, and pass@4. It does not use the
"all attempts must pass" strict interpretation.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def reward_value(trial: dict[str, Any]) -> float:
    rewards = (trial.get("verifier_result") or {}).get("rewards") or {}
    value = rewards.get("reward")
    if value is None:
        return 0.0
    return float(value)


@dataclass
class TrialSummary:
    model: str
    job: str
    task: str
    started_at: str
    reward: float
    cost_usd: float
    wall_s: float | None


def read_trials(job_dir: Path) -> list[TrialSummary]:
    trials: list[TrialSummary] = []
    for trial_dir in sorted(job_dir.iterdir()):
        result_path = trial_dir / "result.json"
        if not trial_dir.is_dir() or not result_path.exists():
            continue
        trial = json.loads(result_path.read_text())
        config = trial.get("config") or {}
        agent = config.get("agent") or {}
        started = trial.get("started_at") or ""
        finished = trial.get("finished_at")
        started_dt = parse_ts(started)
        finished_dt = parse_ts(finished)
        wall_s = None
        if started_dt and finished_dt:
            wall_s = (finished_dt - started_dt).total_seconds()
        trials.append(
            TrialSummary(
                model=agent.get("model_name") or "",
                job=job_dir.name,
                task=trial.get("task_name") or "",
                started_at=started,
                reward=reward_value(trial),
                cost_usd=float((trial.get("agent_result") or {}).get("cost_usd") or 0.0),
                wall_s=wall_s,
            )
        )
    return trials


def is_complete_job(result: dict[str, Any], expected_trials: int) -> bool:
    if result.get("finished_at") is None:
        return False
    if result.get("n_total_trials") != expected_trials:
        return False
    for eval_result in (result.get("stats") or {}).get("evals", {}).values():
        return (eval_result.get("n_trials") or 0) == expected_trials
    return False


def summarize_job(job_dir: Path, expected_trials: int) -> tuple[dict[str, Any], list[TrialSummary]] | None:
    result_path = job_dir / "result.json"
    if not result_path.exists():
        return None
    result = json.loads(result_path.read_text())
    if not is_complete_job(result, expected_trials):
        return None

    trials = read_trials(job_dir)
    if not trials:
        return None

    by_task: dict[str, list[TrialSummary]] = defaultdict(list)
    for trial in trials:
        by_task[trial.task].append(trial)
    for task_trials in by_task.values():
        task_trials.sort(key=lambda trial: trial.started_at)

    pass_at_1 = 0
    pass_at_4 = 0
    for task_trials in by_task.values():
        rewards = [trial.reward for trial in task_trials]
        if rewards and rewards[0] >= 1.0:
            pass_at_1 += 1
        if any(reward >= 1.0 for reward in rewards):
            pass_at_4 += 1

    top_started = parse_ts(result.get("started_at"))
    top_finished = parse_ts(result.get("finished_at"))
    wall_s = None
    if top_started and top_finished:
        wall_s = (top_finished - top_started).total_seconds()

    n_tasks = len(by_task)
    total_cost = sum(trial.cost_usd for trial in trials)
    model = trials[0].model
    mean_reward = sum(trial.reward for trial in trials) / len(trials)
    model_row = {
        "job": job_dir.name,
        "model": model,
        "n_tasks": n_tasks,
        "n_trials": len(trials),
        "mean_reward": mean_reward,
        "pass_at_1": pass_at_1 / n_tasks if n_tasks else 0.0,
        "pass_at_1_count": pass_at_1,
        "pass_at_4": pass_at_4 / n_tasks if n_tasks else 0.0,
        "pass_at_4_count": pass_at_4,
        "total_cost_usd": total_cost,
        "wall_min": wall_s / 60 if wall_s is not None else "",
        "attempts_per_min": len(trials) / (wall_s / 60) if wall_s else "",
    }
    return model_row, trials


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs-dir", default="jobs")
    parser.add_argument("--pattern", default="full25-k4-open-*")
    parser.add_argument("--expected-trials", type=int, default=100)
    parser.add_argument("--models-csv", default="jobs/k4-open-8h-models.csv")
    parser.add_argument("--tasks-csv", default="jobs/k4-open-8h-tasks.csv")
    args = parser.parse_args()

    jobs_dir = Path(args.jobs_dir)
    model_rows: list[dict[str, Any]] = []
    all_trials: list[TrialSummary] = []

    for job_dir in sorted(jobs_dir.glob(args.pattern)):
        if not job_dir.is_dir():
            continue
        summary = summarize_job(job_dir, args.expected_trials)
        if summary is None:
            continue
        model_row, trials = summary
        model_rows.append(model_row)
        all_trials.extend(trials)

    if not model_rows:
        print("No complete k=4 jobs found.")
        return 1

    task_rows: list[dict[str, Any]] = []
    by_task: dict[str, list[TrialSummary]] = defaultdict(list)
    for trial in all_trials:
        by_task[trial.task].append(trial)

    models = {row["model"] for row in model_rows}
    for task, trials in sorted(by_task.items()):
        by_model: dict[str, list[TrialSummary]] = defaultdict(list)
        for trial in trials:
            by_model[trial.model].append(trial)
        models_pass_at_4 = sum(
            1 for model_trials in by_model.values() if any(trial.reward >= 1.0 for trial in model_trials)
        )
        task_rows.append(
            {
                "task": task,
                "n_models": len(models),
                "n_attempts": len(trials),
                "mean_reward": sum(trial.reward for trial in trials) / len(trials),
                "models_pass_at_4": models_pass_at_4,
                "models_pass_at_4_rate": models_pass_at_4 / len(models) if models else 0.0,
            }
        )

    model_rows.sort(key=lambda row: (-float(row["mean_reward"]), row["model"]))
    write_csv(
        Path(args.models_csv),
        model_rows,
        [
            "job",
            "model",
            "n_tasks",
            "n_trials",
            "mean_reward",
            "pass_at_1",
            "pass_at_1_count",
            "pass_at_4",
            "pass_at_4_count",
            "total_cost_usd",
            "wall_min",
            "attempts_per_min",
        ],
    )
    write_csv(
        Path(args.tasks_csv),
        task_rows,
        ["task", "n_models", "n_attempts", "mean_reward", "models_pass_at_4", "models_pass_at_4_rate"],
    )

    print(f"Wrote {args.models_csv}")
    print(f"Wrote {args.tasks_csv}")
    print()
    print("Model summary:")
    for row in model_rows:
        print(
            f"- {row['model']}: mean={row['mean_reward']:.3f}, "
            f"pass@1={row['pass_at_1_count']}/{row['n_tasks']}, "
            f"pass@4={row['pass_at_4_count']}/{row['n_tasks']}, "
            f"cost=${row['total_cost_usd']:.2f}, wall={row['wall_min']:.1f}m"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
