#!/usr/bin/env python3
"""Write or verify the immutable BioTerm-Bench v1.0 task-set receipt."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import tomllib
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ROOT / "configs"
SELECTION = ROOT / "paper" / "generated" / "final-benchmark-selection"
TASK_LIST = CONFIGS / "benchmark_tasks_50.txt"
TASK_TABLE = CONFIGS / "benchmark_v1.0_tasks.tsv"
MANIFEST = CONFIGS / "benchmark_v1.0_manifest.json"
VERSION = "1.0.0"
SELECTION_FILES = (
    SELECTION / "selected_tasks_50.csv",
    SELECTION / "selection_summary.json",
    SELECTION / "all_item_irt.csv",
    SELECTION / "selection_decisions_115.csv",
    SELECTION / "README.md",
    ROOT / "scripts" / "select_final_benchmark.py",
    TASK_LIST,
)


def file_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


#: Paths that are build or interpreter by-products, never task content. The
#: original v1.0 receipt hashed `__pycache__/*.pyc` left behind by local grader
#: runs; git ignores those, so 21 of 50 checksums could not be reproduced from
#: a clean checkout. See `receipt_corrections` in the manifest.
IGNORED_PARTS = {"__pycache__", ".DS_Store"}


def is_task_file(path: Path) -> bool:
    return path.is_file() and not IGNORED_PARTS.intersection(path.parts) and path.suffix != ".pyc"


def directory_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(candidate for candidate in path.rglob("*") if is_task_file(candidate)):
        digest.update(item.relative_to(path).as_posix().encode())
        digest.update(b"\0")
        digest.update(item.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def configured_names(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]


def selection_rows() -> list[dict[str, str]]:
    with (SELECTION / "selected_tasks_50.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    sources = [row["source_task"] for row in rows]
    public_ids = [row["benchmark_id"] for row in rows]
    if len(rows) != 50 or len(set(sources)) != 50 or len(set(public_ids)) != 50:
        raise RuntimeError("final selection must contain 50 unique source and public task IDs")
    if set(sources) != set(configured_names(TASK_LIST)):
        raise RuntimeError("selected_tasks_50.csv and benchmark_tasks_50.txt disagree")
    forbidden = {"confirmed_floor", "confirmed_negative", "uncertain_negative", "clear_ceiling"}
    selected_forbidden = sorted(row["source_task"] for row in rows if row["status"] in forbidden)
    if selected_forbidden:
        raise RuntimeError(f"selection contains forbidden task statuses: {selected_forbidden}")
    return rows


def task_records(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    records = []
    for row in rows:
        task_path = ROOT / "tasks" / row["source_task"]
        if not task_path.is_dir():
            raise RuntimeError(f"missing selected task directory: {task_path}")
        with (task_path / "task.toml").open("rb") as handle:
            config = tomllib.load(handle)
        metadata = config.get("metadata", {})
        environment = config.get("environment", {})
        if metadata.get("category") != row["category"]:
            raise RuntimeError(f"category mismatch for {row['source_task']}")
        records.append(
            {
                "public_id": row["benchmark_id"],
                "source_task": row["source_task"],
                "category": row["category"],
                "docker_image": environment.get("docker_image", ""),
                "task_checksum": directory_checksum(task_path),
            }
        )
    return sorted(records, key=lambda record: str(record["public_id"]))


def image_digest(image: str) -> str | None:
    result = subprocess.run(
        ["docker", "image", "inspect", image, "--format", "{{.Id}}"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or None


def harbor_version() -> str:
    result = subprocess.run(
        ["harbor", "--version"], check=False, capture_output=True, text=True
    )
    return result.stdout.strip() or result.stderr.strip() or "unknown"


def write_table(records: list[dict[str, object]]) -> None:
    with TASK_TABLE.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            ["public_id", "source_task", "category", "docker_image", "task_checksum"],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(records)


def table_rows() -> list[dict[str, str]]:
    with TASK_TABLE.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def task_set_digest(records: list[dict[str, object]]) -> str:
    payload = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def write_freeze() -> None:
    if MANIFEST.exists() or TASK_TABLE.exists():
        raise RuntimeError("v1.0 freeze already exists; use --verify instead of overwriting it")
    if (ROOT / "VERSION").read_text().strip() != VERSION:
        raise RuntimeError("VERSION does not match the release being frozen")
    dataset = json.loads((ROOT / "dataset.json").read_text())
    if dataset.get("version") != VERSION:
        raise RuntimeError("dataset.json version does not match the release being frozen")
    rows = selection_rows()
    records = task_records(rows)
    write_table(records)
    images = sorted({str(record["docker_image"]) for record in records})
    image_digests = {image: image_digest(image) for image in images}
    missing_images = [image for image, digest in image_digests.items() if not digest]
    if missing_images:
        TASK_TABLE.unlink(missing_ok=True)
        raise RuntimeError(f"cannot freeze without local release images: {missing_images}")
    manifest = {
        "benchmark": "BioTerm-Bench",
        "version": VERSION,
        "status": "frozen",
        "frozen_at": datetime.now(UTC).isoformat(),
        "task_count": 50,
        "public_task_ids": "canonical IDs omit internal A-D/nohint suffixes",
        "source_task_list": str(TASK_LIST.relative_to(ROOT)),
        "task_table": str(TASK_TABLE.relative_to(ROOT)),
        "task_set_digest": task_set_digest(records),
        "category_counts": dict(sorted(Counter(str(row["category"]) for row in records).items())),
        "task_images": image_digests,
        "selection_method": "ridge-regularized Rasch/1PL on the complete k1 matrix, followed by psychometric and diversity constraints",
        "selection_artifacts": {
            str(path.relative_to(ROOT)): file_checksum(path) for path in SELECTION_FILES
        },
        "reference_protocol": {
            "agent": "terminus-2",
            "primary_metric": "single-attempt mean reward",
            "grader": "deterministic task verifier",
            "harbor_version_at_freeze": harbor_version(),
        },
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"froze BioTerm-Bench {VERSION}: 50 tasks, digest {manifest['task_set_digest']}")


def verify_freeze() -> None:
    if not MANIFEST.exists() or not TASK_TABLE.exists():
        raise RuntimeError("v1.0 freeze receipt is missing")
    manifest = json.loads(MANIFEST.read_text())
    if manifest.get("version") != VERSION or manifest.get("status") != "frozen":
        raise RuntimeError("unexpected v1.0 manifest identity or status")
    if (ROOT / "VERSION").read_text().strip() != VERSION:
        raise RuntimeError("VERSION changed after freeze")
    if json.loads((ROOT / "dataset.json").read_text()).get("version") != VERSION:
        raise RuntimeError("dataset.json version changed after freeze")
    current = task_records(selection_rows())
    frozen = table_rows()
    if current != frozen:
        now = {str(row["source_task"]): row for row in current}
        then = {str(row["source_task"]): row for row in frozen}
        changed = sorted(
            name for name in now.keys() | then.keys()
            if {k: str(v) for k, v in now.get(name, {}).items()}
            != {k: str(v) for k, v in then.get(name, {}).items()}
        )
        raise RuntimeError(f"v1.0 task table or task contents changed: {changed}")
    if task_set_digest(current) != manifest.get("task_set_digest"):
        raise RuntimeError("v1.0 task-set digest mismatch")
    for relative, expected in manifest.get("selection_artifacts", {}).items():
        path = ROOT / relative
        if not path.is_file() or file_checksum(path) != expected:
            raise RuntimeError(f"frozen selection artifact changed: {relative}")
    image_warnings = []
    for image, expected in manifest.get("task_images", {}).items():
        current_digest = image_digest(image)
        if current_digest and current_digest != expected:
            raise RuntimeError(f"local image digest changed for {image}")
        if not current_digest:
            image_warnings.append(image)
    message = f"verified BioTerm-Bench {VERSION}: 50 frozen tasks"
    if image_warnings:
        message += f" (images unavailable locally: {', '.join(image_warnings)})"
    print(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true", help="create the one-time v1.0 receipt")
    action.add_argument("--verify", action="store_true", help="verify files against the receipt")
    args = parser.parse_args()
    if args.write:
        write_freeze()
    else:
        verify_freeze()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
