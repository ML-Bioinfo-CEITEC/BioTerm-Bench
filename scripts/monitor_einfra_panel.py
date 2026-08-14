#!/usr/bin/env python3
"""Append e-INFRA panel checkpoints for a single Harbor job or a panel manifest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.einfra_panel_common import (
    DEFAULT_MONITOR_PATH,
    PanelEntry,
    append_checkpoint,
    expected_trials,
    monitor_payload,
    read_job_status,
    read_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("configs/einfra_panel.tsv"))
    parser.add_argument("--job-path", type=Path, required=True)
    parser.add_argument("--model-slug", required=True)
    parser.add_argument("--attempts", type=int, default=4)
    parser.add_argument("--task-count", type=int, required=True)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--snapshot-dir", type=Path, default=None)
    parser.add_argument("--monitor-path", type=Path, default=DEFAULT_MONITOR_PATH)
    parser.add_argument("--event", default="manual-monitor")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    entries = {entry.slug: entry for entry in read_manifest(args.manifest)}
    if args.model_slug not in entries:
        raise SystemExit(f"Unknown model slug in manifest: {args.model_slug}")
    entry: PanelEntry = entries[args.model_slug]
    expected = expected_trials(attempts=args.attempts, task_count=args.task_count)
    _ = read_job_status(args.job_path, expected)
    append_checkpoint(
        args.monitor_path,
        monitor_payload(
            entry=entry,
            job_path=args.job_path,
            expected=expected,
            concurrent_trials=args.concurrency,
            snapshot_dir=args.snapshot_dir,
            event=args.event,
        ),
    )
    print(args.monitor_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
