"""Shared parsing and integrity helpers for the pre-IRT campaign."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONFIGS = ROOT / "configs"
JOBS = ROOT / "jobs"


def configured_names(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]


def checksum_directory(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(item.relative_to(path).as_posix().encode())
        digest.update(b"\0")
        digest.update(item.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def assert_frozen_tasks() -> list[str]:
    tasks = configured_names(CONFIGS / "preirt_tasks_113.txt")
    if len(tasks) != 113 or len(set(tasks)) != 113:
        raise RuntimeError("pre-IRT task manifest must contain 113 unique tasks")
    expected: dict[str, str] = {}
    with (CONFIGS / "preirt_task_checksums.tsv").open() as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["included"] == "True":
                expected[row["task"]] = row["checksum"]
    if set(tasks) != set(expected):
        raise RuntimeError("task list and checksum manifest disagree")
    changed = [
        task
        for task in tasks
        if checksum_directory(ROOT / "tasks" / task) != expected[task]
    ]
    if changed:
        raise RuntimeError(f"frozen task checksum mismatch: {changed}")
    return tasks


def load_panel() -> list[dict[str, str]]:
    with (CONFIGS / "preirt_panel.tsv").open() as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if len(rows) != 10 or len({row["deployment"] for row in rows}) != 10:
        raise RuntimeError("pre-IRT panel must contain ten unique deployments")
    return rows


def job_complete(job: Path, expected_trials: int) -> bool:
    result = job / "result.json"
    if not result.exists():
        return False
    try:
        data = json.loads(result.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    return bool(data.get("finished_at")) and data.get("stats", {}).get("n_trials") == expected_trials


def job_scored_complete(job: Path, expected_trials: int) -> bool:
    rows = trial_records(job)
    return job_complete(job, expected_trials) and len(rows) == expected_trials and all(
        row["reward"] is not None for row in rows
    )


def trial_records(job: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted(job.glob("*/result.json")):
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        reward = (
            (data.get("verifier_result") or {}).get("rewards") or {}
        ).get("reward")
        records.append(
            {
                "task": data.get("task_name"),
                "trial": data.get("trial_name"),
                "reward": None if data.get("exception_info") else reward,
                "error": data.get("exception_info"),
                "cost_usd": (data.get("agent_result") or {}).get("cost_usd") or 0.0,
                "started_at": data.get("started_at"),
                "finished_at": data.get("finished_at"),
                "task_checksum": data.get("task_checksum"),
                "path": str(path.parent),
            }
        )
    return records


def campaign_cost() -> float:
    total = 0.0
    for job in JOBS.glob("preirt-*-or-*"):
        if job.is_dir():
            total += sum(float(row["cost_usd"]) for row in trial_records(job))
    return total


def assignments() -> dict[str, list[str]]:
    path = CONFIGS / "preirt_followup_assignments.tsv"
    grouped: dict[str, list[str]] = defaultdict(list)
    if not path.exists():
        return grouped
    with path.open() as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            grouped[row["deployment"]].append(row["task"])
    return grouped
