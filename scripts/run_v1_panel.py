#!/usr/bin/env python3
"""Run or resume one append-only provider lane on frozen BioTerm-Bench v1.0."""

from __future__ import annotations

import argparse
import os
import subprocess
import time
from pathlib import Path

from preirt_common import trial_records
from v1_panel_common import (
    JOBS,
    PAUSE_MARKER,
    ROOT,
    append_event,
    freeze_digest,
    job_name,
    job_scored_complete,
    live_model_ids,
    load_panel,
    openrouter_campaign_cost,
    provider_token,
    source_tasks,
)

SMOKE_TASK = "flagstat-report"
COOLDOWNS = (60, 900, 1800, 3600)


def provider_environment(provider: str, token: str) -> dict[str, str]:
    env = os.environ.copy()
    if provider in {"openrouter", "einfra"}:
        env["OPENAI_API_KEY"] = token
    if provider == "openrouter":
        env["OPENROUTER_API_KEY"] = token
    return env


def start_command(
    row: dict[str, str], tasks: list[str], *, job: str, concurrency: int
) -> list[str]:
    command = [
        "harbor",
        "run",
        "--path",
        "tasks/",
        "--agent",
        "terminus-2",
        "-m",
        row["model_id"],
        "--no-delete",
        "-n",
        str(concurrency),
        "-k",
        "1",
        "--timeout-multiplier",
        "1.5",
        "--job-name",
        job,
        "--jobs-dir",
        "jobs",
        "-y",
        "--artifact",
        "/tmp/terminus2",
    ]
    if row["api_base"]:
        command.extend(["--ak", f"api_base={row['api_base'].rstrip('/')}/"])
    for task in tasks:
        command.extend(["--include-task-name", task])
    return command


def resume_command(path: Path) -> list[str]:
    command = ["harbor", "job", "resume", "--job-path", str(path)]
    error_types = {
        (row["error"] or {}).get("exception_type")
        for row in trial_records(path)
        if row["error"]
    }
    for error_type in sorted(value for value in error_types if value):
        command.extend(["--filter-error-type", error_type])
    return command


def log_has(path: Path, *needles: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(errors="ignore")[-150_000:].lower()
    return any(needle.lower() in text for needle in needles)


def run_job(
    row: dict[str, str],
    tasks: list[str],
    *,
    name: str,
    token: str,
    concurrency: int,
    expected: int,
) -> bool:
    path = JOBS / name
    log_path = JOBS / f"{name}.log"
    if job_scored_complete(path, expected):
        append_event("skip_complete", deployment=row["deployment"], job=name)
        return True
    for recovery_index, cooldown in enumerate(COOLDOWNS, start=1):
        if PAUSE_MARKER.exists():
            append_event("paused_before_job", deployment=row["deployment"], job=name)
            return False
        command = resume_command(path) if (path / "config.json").exists() else start_command(
            row, tasks, job=name, concurrency=concurrency
        )
        append_event(
            "job_start",
            deployment=row["deployment"],
            provider=row["provider"],
            job=name,
            recovery_index=recovery_index,
            tasks=len(tasks),
        )
        with log_path.open("a") as log:
            subprocess.run(
                command,
                cwd=ROOT,
                env=provider_environment(row["provider"], token),
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        if job_scored_complete(path, expected):
            append_event("job_complete", deployment=row["deployment"], job=name, trials=expected)
            return True
        if log_has(log_path, "401", "403", "unauthorized", "forbidden"):
            append_event("provider_auth_block", deployment=row["deployment"], job=name)
            raise RuntimeError(f"{row['provider']} authentication failed; credentials must be renewed")
        if log_has(log_path, "429", "rate limit", "too many requests"):
            wait = max(cooldown, 900)
            append_event("rate_limit_cooldown", deployment=row["deployment"], job=name, seconds=wait)
            time.sleep(wait)
            continue
        append_event("technical_recovery", deployment=row["deployment"], job=name, seconds=cooldown)
        time.sleep(cooldown)
    append_event("job_incomplete", deployment=row["deployment"], job=name)
    return False


def smoke_name(deployment: str) -> str:
    return f"v1-smoke-{deployment}"


def run_deployment(
    row: dict[str, str], *, target_attempts: int, token: str, concurrency: int
) -> None:
    smoke = smoke_name(row["deployment"])
    if not run_job(
        row,
        [SMOKE_TASK],
        name=smoke,
        token=token,
        concurrency=1,
        expected=1,
    ):
        append_event("model_smoke_incomplete", deployment=row["deployment"])
        return
    tasks = source_tasks()
    for attempt in range(1, target_attempts + 1):
        if PAUSE_MARKER.exists():
            return
        name = job_name(row["deployment"], attempt)
        if not run_job(
            row,
            tasks,
            name=name,
            token=token,
            concurrency=concurrency,
            expected=len(tasks),
        ):
            append_event("model_wave_incomplete", deployment=row["deployment"], attempt=attempt)
            return
        if row["provider"] == "openrouter":
            append_event(
                "openrouter_cost",
                deployment=row["deployment"],
                cumulative_usd=openrouter_campaign_cost(),
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=("openrouter", "einfra", "local"), required=True)
    parser.add_argument("--target-attempts", type=int, choices=range(1, 6), default=1)
    parser.add_argument("--only", default="", help="comma-separated deployment IDs")
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--openrouter-budget", type=float, default=150.0)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.concurrency < 1 or args.concurrency > 2:
        raise RuntimeError("per-provider concurrency must be 1 or 2")
    if PAUSE_MARKER.exists():
        raise RuntimeError("v1 campaign is paused; use scripts/v1_panel_control.sh resume")
    digest = freeze_digest()
    subprocess.run(
        ["python3", "scripts/freeze_benchmark_v1.py", "--verify"], cwd=ROOT, check=True
    )
    selected = {value for value in args.only.split(",") if value}
    panel = [row for row in load_panel() if row["provider"] == args.provider]
    if selected:
        missing = selected - {row["deployment"] for row in panel}
        if missing:
            raise RuntimeError(f"unknown deployment IDs for {args.provider}: {sorted(missing)}")
        panel = [row for row in panel if row["deployment"] in selected]
    if not panel:
        print(f"no {args.provider} deployments configured")
        return 0
    token = provider_token(args.provider)
    live = None if args.provider == "local" else live_model_ids(args.provider, token)
    available = [row for row in panel if live is None or row["api_model_id"] in live]
    unavailable = [row for row in panel if live is not None and row["api_model_id"] not in live]
    for row in unavailable:
        append_event(
            "model_unavailable",
            deployment=row["deployment"],
            provider=args.provider,
            api_model_id=row["api_model_id"],
        )
    append_event(
        "lane_start",
        provider=args.provider,
        target_attempts=args.target_attempts,
        configured=len(panel),
        available=len(available),
        task_set_digest=digest,
    )
    print(
        f"validated {len(available)}/{len(panel)} available {args.provider} deployments; "
        f"target k={args.target_attempts}"
    )
    if args.validate_only:
        return 0
    for row in available:
        if PAUSE_MARKER.exists():
            break
        if args.provider == "openrouter" and openrouter_campaign_cost() >= args.openrouter_budget:
            append_event("budget_stop", provider="openrouter", cap_usd=args.openrouter_budget)
            raise RuntimeError(f"OpenRouter v1 campaign reached ${args.openrouter_budget:.2f}")
        run_deployment(
            row,
            target_attempts=args.target_attempts,
            token=token,
            concurrency=args.concurrency,
        )
    append_event("lane_stop", provider=args.provider, paused=PAUSE_MARKER.exists())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
