#!/usr/bin/env python3
"""Lint every BioTerm-Bench task directory.

Exits 0 iff every task under ``tasks/`` passes the structural checks
described in ``docs/task-authoring.md``. Exits 0 with a short note when
no tasks are present (the repo's initial state).

Checks per task:
  * required files exist (task.toml, instruction.md, solution/solve.sh,
    tests/test.sh, tests/check.py, data/, gold/)
  * task.toml parses and contains the required fields
  * instruction.md word count is < 200
  * solution/solve.sh has a shebang and no ``TODO`` markers
  * tests/test.sh writes a reward to /logs/verifier/reward.txt

Run as:
    python3 scripts/validate_task.py
    python3 scripts/validate_task.py --tasks-dir tasks/
    python3 scripts/validate_task.py --only bam-sort-index
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable

import click

try:
    import tomllib  # type: ignore[attr-defined]  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - fallback for 3.10
    import tomli as tomllib  # type: ignore[no-redef]

VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_CATEGORIES = {
    "alignment",
    "variant",
    "rnaseq",
    "db",
    "search",
    "qc",
    "metadata",
    "synthesis",
}

REQUIRED_FILES = [
    "task.toml",
    "instruction.md",
    "solution/solve.sh",
    "tests/test.sh",
    "tests/check.py",
]
REQUIRED_DIRS = ["data", "gold"]

REQUIRED_TOML = {
    "metadata": ["author_name", "author_email", "difficulty", "category", "tags"],
    "verifier": ["timeout_sec"],
    "agent": ["timeout_sec"],
    "environment": ["docker_image", "cpus", "memory", "storage"],
}

MAX_INSTRUCTION_WORDS = 200
REWARD_PATH = "/logs/verifier/reward.txt"


class TaskError(Exception):
    """One validation failure in a task directory."""


def _check_files(task_dir: Path) -> list[str]:
    errors: list[str] = []
    for rel in REQUIRED_FILES:
        p = task_dir / rel
        if not p.is_file():
            errors.append(f"missing file: {rel}")
    for rel in REQUIRED_DIRS:
        p = task_dir / rel
        if not p.is_dir():
            errors.append(f"missing directory: {rel}/")
    return errors


def _check_toml(task_dir: Path) -> list[str]:
    errors: list[str] = []
    toml_path = task_dir / "task.toml"
    if not toml_path.is_file():
        return ["task.toml missing, skipping toml checks"]
    try:
        data = tomllib.loads(toml_path.read_text())
    except Exception as exc:  # pragma: no cover - toml parser diversity
        return [f"task.toml failed to parse: {exc}"]

    for section, keys in REQUIRED_TOML.items():
        if section not in data:
            errors.append(f"task.toml missing [{section}] section")
            continue
        for key in keys:
            if key not in data[section]:
                errors.append(f"task.toml missing {section}.{key}")

    meta = data.get("metadata", {})
    difficulty = meta.get("difficulty")
    if difficulty is not None and difficulty not in VALID_DIFFICULTIES:
        errors.append(
            f"task.toml metadata.difficulty={difficulty!r} "
            f"not in {sorted(VALID_DIFFICULTIES)}"
        )
    category = meta.get("category")
    if category is not None and category not in VALID_CATEGORIES:
        errors.append(
            f"task.toml metadata.category={category!r} "
            f"not in {sorted(VALID_CATEGORIES)}"
        )
    return errors


def _check_instruction(task_dir: Path) -> list[str]:
    p = task_dir / "instruction.md"
    if not p.is_file():
        return []
    text = p.read_text()
    words = len(text.split())
    if words >= MAX_INSTRUCTION_WORDS:
        return [
            f"instruction.md is {words} words (limit {MAX_INSTRUCTION_WORDS - 1})"
        ]
    return []


def _check_solve(task_dir: Path) -> list[str]:
    p = task_dir / "solution" / "solve.sh"
    if not p.is_file():
        return []
    errors: list[str] = []
    text = p.read_text()
    first_line = text.splitlines()[0] if text else ""
    if not first_line.startswith("#!"):
        errors.append("solution/solve.sh is missing a shebang")
    if re.search(r"\bTODO\b", text):
        errors.append("solution/solve.sh contains a TODO marker")
    return errors


def _check_test_sh(task_dir: Path) -> list[str]:
    p = task_dir / "tests" / "test.sh"
    if not p.is_file():
        return []
    text = p.read_text()
    if REWARD_PATH not in text:
        return [f"tests/test.sh does not reference {REWARD_PATH}"]
    return []


def _validate_one(task_dir: Path) -> list[str]:
    errors: list[str] = []
    errors += _check_files(task_dir)
    errors += _check_toml(task_dir)
    errors += _check_instruction(task_dir)
    errors += _check_solve(task_dir)
    errors += _check_test_sh(task_dir)
    return errors


def _iter_tasks(tasks_dir: Path, only: str | None) -> Iterable[Path]:
    if not tasks_dir.exists():
        return []
    for child in sorted(tasks_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith("."):
            continue
        if only is not None and child.name != only:
            continue
        yield child


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--tasks-dir",
    "tasks_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("tasks"),
    show_default=True,
    help="Directory containing task subdirectories.",
)
@click.option(
    "--only",
    type=str,
    default=None,
    help="Only validate this single task (by directory name).",
)
def main(tasks_dir: Path, only: str | None) -> None:
    """Lint every BioTerm-Bench task directory."""
    tasks = list(_iter_tasks(tasks_dir, only))
    if not tasks:
        click.echo(f"no tasks found under {tasks_dir}/ (nothing to validate)")
        sys.exit(0)

    total_failures = 0
    for task_dir in tasks:
        errors = _validate_one(task_dir)
        if errors:
            total_failures += 1
            click.echo(f"FAIL {task_dir.name}")
            for err in errors:
                click.echo(f"  - {err}")
        else:
            click.echo(f"ok   {task_dir.name}")

    click.echo()
    click.echo(f"{len(tasks)} tasks checked, {total_failures} failed")
    sys.exit(1 if total_failures else 0)


if __name__ == "__main__":
    main()
