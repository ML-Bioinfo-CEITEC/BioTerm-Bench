#!/usr/bin/env python3
"""Run the exact e-INFRA model panel through Harbor Terminus-2."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.einfra_panel_common import (
    DEFAULT_ATTEMPTS,
    DEFAULT_BASE_URL,
    DEFAULT_MONITOR_PATH,
    DEFAULT_RETAINED_TASK_LIST,
    DEFAULT_SELECTION_RECEIPT,
    DEFAULT_SNAPSHOT_ROOT,
    SMOKE_TASKS,
    PanelEntry,
    append_checkpoint,
    build_agent_env,
    build_harbor_resume_command,
    build_harbor_start_command,
    choose_next_concurrency,
    classify_job_failures,
    count_task_dirs,
    ensure_model_available,
    ensure_token,
    expected_trials,
    filter_manifest,
    iso_now,
    job_dir,
    job_log_path,
    monitor_payload,
    read_job_status,
    read_manifest,
    require_selected_task_names,
    run_subprocess,
    safe_command_for_log,
    sleep_with_checkpoints,
    smoke_protocol_failures,
    snapshot_provider_state,
    validate_manifest_live,
    write_json,
)
from scripts.einfra_panel_common import (
    PANEL_INITIAL_CONCURRENCY as START_CONCURRENCY,
)

COOLDOWNS = [15 * 60, 30 * 60, 60 * 60]


def checkpoint_writer(
    monitor_path: Path,
    entry: PanelEntry,
    current_job_dir: Path,
    expected: int,
    concurrency: int,
    snapshot_dir: Path | None,
):
    def _write(event: str) -> bool:
        payload = monitor_payload(
            entry=entry,
            job_path=current_job_dir,
            expected=expected,
            concurrent_trials=concurrency,
            snapshot_dir=snapshot_dir,
            event=event,
        )
        append_checkpoint(monitor_path, payload)
        return not bool(payload.get("stalled") or payload.get("persistent_queue"))

    return _write


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("configs/einfra_panel.tsv"))
    parser.add_argument("--tasks-path", type=Path, default=Path("tasks"))
    parser.add_argument("--task-list", type=Path, default=DEFAULT_RETAINED_TASK_LIST)
    parser.add_argument("--selection-receipt", type=Path, default=DEFAULT_SELECTION_RECEIPT)
    parser.add_argument(
        "--allow-explicit-task-list",
        action="store_true",
        help="Use --task-list verbatim (for the separately labelled core-25 scope).",
    )
    parser.add_argument(
        "--full-job-prefix",
        default="einfra-k4",
        help="Prefix for non-smoke jobs; use a distinct prefix for each score scope.",
    )
    parser.add_argument("--jobs-dir", type=Path, default=Path("jobs"))
    parser.add_argument("--monitor-path", type=Path, default=DEFAULT_MONITOR_PATH)
    parser.add_argument("--snapshot-root", type=Path, default=DEFAULT_SNAPSHOT_ROOT)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--attempts", type=int, default=DEFAULT_ATTEMPTS)
    parser.add_argument("--only-models", default="")
    parser.add_argument("--start-from", default="")
    parser.add_argument("--skip-completed", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--smoke", action="store_true", help="Run smoke-only against three representative tasks."
    )
    parser.add_argument(
        "--write-status-json", type=Path, default=Path("jobs/einfra-panel-status.json")
    )
    return parser.parse_args()


def run_one_job(
    *,
    entry: PanelEntry,
    tasks_path: Path,
    jobs_dir: Path,
    task_names: list[str],
    attempts: int,
    concurrency: int,
    base_url: str,
    token: str,
    monitor_path: Path,
    snapshot_dir: Path | None,
    smoke: bool,
    dry_run: bool,
    skip_completed: bool,
    full_job_prefix: str = "einfra-k4",
) -> tuple[str, set[str], int]:
    selected_tasks = SMOKE_TASKS if smoke else task_names
    task_count = (
        len(selected_tasks) if selected_tasks else count_task_dirs(tasks_path, task_names or None)
    )
    job_name = entry.smoke_job_name if smoke else f"{full_job_prefix}-{entry.slug}"
    expected = expected_trials(attempts=attempts, task_count=task_count)
    current_job_dir = job_dir(jobs_dir, job_name)
    checkpoint = checkpoint_writer(
        monitor_path, entry, current_job_dir, expected, concurrency, snapshot_dir
    )

    status = read_job_status(current_job_dir, expected)
    if status.state == "complete" and skip_completed:
        signals = classify_job_failures(current_job_dir)
        if smoke and smoke_protocol_failures(current_job_dir) >= len(SMOKE_TASKS):
            signals.add("protocol")
        checkpoint("skip-complete")
        return status.state, signals, status.completed_trials

    if current_job_dir.exists() and status.state != "missing":
        cmd = build_harbor_resume_command(current_job_dir)
    else:
        cmd = build_harbor_start_command(
            entry,
            tasks_path=tasks_path,
            jobs_dir=jobs_dir,
            job_name=job_name,
            attempts=attempts,
            concurrent_trials=concurrency,
            task_names=selected_tasks,
            task_name=None,
            api_base=base_url,
        )

    checkpoint("start")
    if dry_run:
        print(safe_command_for_log(cmd))
        checkpoint("dry-run")
        return "dry-run", set(), status.completed_trials

    env = build_agent_env(token)
    preexisting_results = set(current_job_dir.glob("*/result.json"))
    log_path = job_log_path(current_job_dir)
    log_start_offset = log_path.stat().st_size if log_path.exists() else 0
    exit_code = run_subprocess(
        cmd,
        env=env,
        log_path=log_path,
        checkpoint_cb=lambda: checkpoint("interval"),
    )
    status = read_job_status(current_job_dir, expected)
    signals = classify_job_failures(
        current_job_dir,
        log_start_offset=log_start_offset,
        trial_results=set(current_job_dir.glob("*/result.json")) - preexisting_results,
    )
    checkpoint(f"exit:{exit_code}")

    if smoke and smoke_protocol_failures(current_job_dir) >= len(SMOKE_TASKS):
        signals.add("protocol")
    post_run = monitor_payload(
        entry=entry,
        job_path=current_job_dir,
        expected=expected,
        concurrent_trials=concurrency,
        snapshot_dir=snapshot_dir,
        event="post-run",
    )
    if post_run["stalled"]:
        signals.add("stalled")
    if post_run["persistent_queue"]:
        signals.add("queue")
    if status.state == "complete":
        return "complete", signals, status.completed_trials
    if "auth" in signals:
        return "auth", signals, status.completed_trials
    if "offline" in signals:
        return "offline", signals, status.completed_trials
    if exit_code == 0 and status.state != "complete":
        return "incomplete", signals, status.completed_trials
    return "failed", signals, status.completed_trials


def main() -> int:
    args = parse_args()
    rows = read_manifest(args.manifest)
    rows = filter_manifest(
        rows,
        only_models={x for x in args.only_models.split(",") if x} or None,
        start_from=args.start_from or None,
    )

    token = ensure_token()
    exact_ids, missing = validate_manifest_live(rows, token, args.base_url)
    print(f"Validated live /v1/models lookup for {len(exact_ids)} exact IDs.")
    if missing:
        print("Missing exact IDs:")
        for model_id in missing:
            print(f"  - {model_id}")
        if args.validate_only:
            return 1
    if args.validate_only:
        return 0

    if args.smoke:
        task_names = list(SMOKE_TASKS)
    elif args.allow_explicit_task_list:
        task_names = [
            line.strip()
            for line in args.task_list.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if not task_names or any(not (args.tasks_path / task).is_dir() for task in task_names):
            raise RuntimeError("explicit task list is empty or contains unknown task names")
    else:
        task_names = require_selected_task_names(args.task_list, args.selection_receipt)
    snapshot_dir = snapshot_provider_state(
        manifest_path=args.manifest,
        snapshot_root=args.snapshot_root,
        token=token,
        base_url=args.base_url,
    )

    status_payload = {
        "started_at": iso_now(),
        "base_url": args.base_url,
        "manifest": str(args.manifest),
        "task_list": str(args.task_list) if args.task_list else None,
        "models": [row.slug for row in rows],
        "current_concurrency": START_CONCURRENCY,
        "snapshot_dir": str(snapshot_dir),
        "results": [],
    }
    write_json(args.write_status_json, status_payload)

    current_concurrency = START_CONCURRENCY
    throttle_index = 0
    revisit: list[PanelEntry] = []

    for phase in ("primary", "revisit"):
        phase_rows = rows if phase == "primary" else revisit
        if not phase_rows:
            continue
        if phase == "revisit":
            revisit = []

        for entry in phase_rows:
            if entry.bare_model_id in missing:
                available = ensure_model_available(entry=entry, token=token, base_url=args.base_url)
                if not available:
                    append_checkpoint(
                        args.monitor_path,
                        {
                            "timestamp": iso_now(),
                            "event": "model-unavailable",
                            "model_slug": entry.slug,
                            "model_id": entry.model_id,
                            "retry_window_seconds": 3600,
                        },
                    )
                    if phase == "primary":
                        revisit.append(entry)
                    else:
                        status_payload["results"].append(
                            {
                                "model": entry.slug,
                                "phase": phase,
                                "status": "offline-after-revisit",
                                "signals": ["offline"],
                            }
                        )
                        write_json(args.write_status_json, status_payload)
                    continue

            # smoke first
            smoke_state, smoke_signals, _smoke_completed = run_one_job(
                entry=entry,
                tasks_path=args.tasks_path,
                jobs_dir=args.jobs_dir,
                task_names=task_names,
                attempts=1,
                concurrency=1,
                base_url=args.base_url,
                token=token,
                monitor_path=args.monitor_path,
                snapshot_dir=snapshot_dir,
                smoke=True,
                dry_run=args.dry_run,
                skip_completed=args.skip_completed,
                full_job_prefix=args.full_job_prefix,
            )
            if smoke_state == "auth":
                raise RuntimeError(
                    "e-INFRA returned 401/403 during smoke test; renew EINFRA_AI_TOKEN"
                )
            if "protocol" in smoke_signals:
                result = {
                    "model": entry.slug,
                    "phase": phase,
                    "status": "incompatible-smoke",
                    "signals": sorted(smoke_signals),
                }
                status_payload["results"].append(result)
                write_json(args.write_status_json, status_payload)
                continue
            if smoke_state == "offline":
                if phase == "primary":
                    revisit.append(entry)
                else:
                    status_payload["results"].append(
                        {
                            "model": entry.slug,
                            "phase": phase,
                            "status": "offline-after-revisit",
                            "signals": sorted(smoke_signals),
                        }
                    )
                    write_json(args.write_status_json, status_payload)
                continue
            if smoke_state not in {"complete", "dry-run"}:
                status_payload["results"].append(
                    {
                        "model": entry.slug,
                        "phase": phase,
                        "status": "smoke-inconclusive",
                        "signals": sorted(smoke_signals),
                    }
                )
                write_json(args.write_status_json, status_payload)
                if phase == "primary":
                    revisit.append(entry)
                continue
            if args.smoke:
                status_payload["results"].append(
                    {
                        "model": entry.slug,
                        "phase": phase,
                        "status": smoke_state,
                        "signals": sorted(smoke_signals),
                    }
                )
                write_json(args.write_status_json, status_payload)
                continue

            throttle_index = 0
            attempts_left = len(COOLDOWNS) + 1
            while attempts_left > 0:
                job_state, signals, completed_trials = run_one_job(
                    entry=entry,
                    tasks_path=args.tasks_path,
                    jobs_dir=args.jobs_dir,
                    task_names=task_names,
                    attempts=args.attempts,
                    concurrency=current_concurrency,
                    base_url=args.base_url,
                    token=token,
                    monitor_path=args.monitor_path,
                    snapshot_dir=snapshot_dir,
                    smoke=False,
                    dry_run=args.dry_run,
                    skip_completed=args.skip_completed,
                    full_job_prefix=args.full_job_prefix,
                )

                if job_state == "auth":
                    raise RuntimeError(
                        "e-INFRA returned 401/403 during panel run; renew EINFRA_AI_TOKEN"
                    )

                if job_state == "complete" or job_state == "dry-run":
                    current_concurrency = choose_next_concurrency(
                        current=current_concurrency,
                        first_model_signals=signals,
                        completed_trials=completed_trials,
                    )
                    throttle_index = 0
                    status_payload["current_concurrency"] = current_concurrency
                    status_payload["results"].append(
                        {
                            "model": entry.slug,
                            "phase": phase,
                            "status": job_state,
                            "signals": sorted(signals),
                            "completed_trials": completed_trials,
                        }
                    )
                    write_json(args.write_status_json, status_payload)
                    break

                if job_state == "offline":
                    if phase == "primary":
                        revisit.append(entry)
                    status_payload["results"].append(
                        {
                            "model": entry.slug,
                            "phase": phase,
                            "status": "offline",
                            "signals": sorted(signals),
                        }
                    )
                    write_json(args.write_status_json, status_payload)
                    break

                if {"rate_limit", "server", "timeout", "queue"} & signals:
                    current_concurrency = 1
                    if attempts_left == 1:
                        attempts_left = 0
                        continue
                    cooldown = COOLDOWNS[min(throttle_index, len(COOLDOWNS) - 1)]
                    throttle_index += 1
                    append_checkpoint(
                        args.monitor_path,
                        {
                            "timestamp": iso_now(),
                            "event": "cooldown",
                            "model_slug": entry.slug,
                            "signals": sorted(signals),
                            "cooldown_seconds": cooldown,
                        },
                    )
                    if args.dry_run:
                        break
                    sleep_with_checkpoints(
                        cooldown,
                        label=f"{entry.slug}:{','.join(sorted(signals))}",
                        checkpoint_cb=checkpoint_writer(
                            args.monitor_path,
                            entry,
                            job_dir(args.jobs_dir, entry.full_job_name),
                            expected_trials(
                                attempts=args.attempts,
                                task_count=count_task_dirs(args.tasks_path, task_names or None),
                            ),
                            current_concurrency,
                            snapshot_dir,
                        ),
                    )
                    attempts_left -= 1
                    continue
                if "stalled" in signals:
                    append_checkpoint(
                        args.monitor_path,
                        {
                            "timestamp": iso_now(),
                            "event": "stall-resume",
                            "model_slug": entry.slug,
                            "job_path": str(job_dir(args.jobs_dir, entry.full_job_name)),
                        },
                    )
                    attempts_left -= 1
                    continue

                status_payload["results"].append(
                    {
                        "model": entry.slug,
                        "phase": phase,
                        "status": job_state,
                        "signals": sorted(signals),
                        "completed_trials": completed_trials,
                    }
                )
                write_json(args.write_status_json, status_payload)
                break
            else:
                status_payload["results"].append(
                    {
                        "model": entry.slug,
                        "phase": phase,
                        "status": "retries-exhausted",
                        "signals": sorted(signals),
                        "completed_trials": completed_trials,
                    }
                )
                write_json(args.write_status_json, status_payload)

    status_payload["finished_at"] = iso_now()
    write_json(args.write_status_json, status_payload)
    print(json.dumps(status_payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
