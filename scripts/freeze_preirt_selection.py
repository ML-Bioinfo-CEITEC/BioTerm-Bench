#!/usr/bin/env python3
"""Freeze the pre-IRT task universe, checksums, and execution manifest."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS = ROOT / "tasks"
CONFIGS = ROOT / "configs"


def names(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]


def task_checksum(task: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in task.rglob("*") if p.is_file()):
        relative = path.relative_to(task).as_posix()
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def image_digest(image: str) -> str | None:
    result = subprocess.run(
        ["docker", "image", "inspect", image, "--format", "{{.Id}}"],
        check=False,
        capture_output=True,
        text=True,
    )
    value = result.stdout.strip()
    return value or None


def main() -> int:
    universe = names(CONFIGS / "all_tasks.txt")
    excluded = set(names(CONFIGS / "preirt_excluded_tasks.txt"))
    retired = set(names(CONFIGS / "retired_tasks.txt"))
    directories = {path.name for path in TASKS.iterdir() if path.is_dir()}

    if len(universe) != 115 or len(set(universe)) != 115:
        raise SystemExit("configs/all_tasks.txt must contain 115 unique active tasks")
    if set(universe) - directories:
        raise SystemExit(f"missing task directories: {sorted(set(universe) - directories)}")
    if excluded != {"fastq-paired-adapter-qc", "mini-align-call-filter"}:
        raise SystemExit(f"unexpected exclusion set: {sorted(excluded)}")
    if set(universe) & retired:
        raise SystemExit("active universe unexpectedly contains a retired task")

    included = sorted(set(universe) - excluded)
    if len(included) != 113:
        raise SystemExit(f"expected 113 included tasks, found {len(included)}")

    records = []
    images = set()
    for name in sorted(universe):
        task = TASKS / name
        toml = (task / "task.toml").read_text()
        category = next(
            line.split("=", 1)[1].strip().strip('"')
            for line in toml.splitlines()
            if line.strip().startswith("category")
        )
        image = next(
            line.split("=", 1)[1].strip().strip('"')
            for line in toml.splitlines()
            if line.strip().startswith("docker_image")
        )
        images.add(image)
        records.append(
            {
                "task": name,
                "included": name in included,
                "category": category,
                "docker_image": image,
                "checksum": task_checksum(task),
                "note": "fundamentally underspecified" if name in excluded else "",
            }
        )

    (CONFIGS / "preirt_tasks_113.txt").write_text("".join(f"{x}\n" for x in included))
    with (CONFIGS / "preirt_task_checksums.tsv").open("w") as handle:
        handle.write("task\tincluded\tcategory\tdocker_image\tchecksum\tnote\n")
        for row in records:
            handle.write(
                "\t".join(
                    str(row[key])
                    for key in ("task", "included", "category", "docker_image", "checksum", "note")
                )
                + "\n"
            )

    manifest = {
        "frozen_at": datetime.now(UTC).isoformat(),
        "task_universe_count": 115,
        "included_task_count": 113,
        "excluded_tasks": sorted(excluded),
        "retired_tasks": sorted(retired),
        "attempts_initial": 1,
        "attempts_maximum": 3,
        "openrouter_budget_usd": 150,
        "agent": "terminus-2",
        "panel_file": "configs/preirt_panel.tsv",
        "task_file": "configs/preirt_tasks_113.txt",
        "checksum_file": "configs/preirt_task_checksums.tsv",
        "image_digests": {image: image_digest(image) for image in sorted(images)},
    }
    (CONFIGS / "preirt_run_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    print("frozen 115-task audit universe; 113 tasks included for screening")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
