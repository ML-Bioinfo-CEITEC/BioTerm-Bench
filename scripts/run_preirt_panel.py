#!/usr/bin/env python3
"""Run or resume one provider lane of the frozen pre-IRT campaign."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from preirt_common import (
    JOBS,
    ROOT,
    assert_frozen_tasks,
    assignments,
    campaign_cost,
    job_scored_complete,
    load_panel,
    trial_records,
)

EINFRA_BASE = "https://llm.ai.e-infra.cz/v1"
BUDGET_USD = 150.0


def dotenv_value(name: str) -> str | None:
    path = ROOT / ".env"
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def provider_token(provider: str) -> str:
    if provider == "openrouter":
        value = os.environ.get("OPENROUTER_API_KEY")
    else:
        value = (
            os.environ.get("EINFRA_AI_TOKEN")
            or os.environ.get("E_INFRA_API_KEY")
            or dotenv_value("E_INFRA_API_KEY")
        )
    if not value:
        raise RuntimeError(f"credential for {provider} is unavailable")
    return value


def live_model_ids(provider: str, token: str) -> set[str]:
    url = "https://openrouter.ai/api/v1/models" if provider == "openrouter" else EINFRA_BASE + "/models"
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    return {row["id"] for row in payload.get("data", [])}


def api_model_id(row: dict[str, str]) -> str:
    prefix = "openrouter/" if row["provider"] == "openrouter" else "openai/"
    return row["model_id"].removeprefix(prefix)


def note(event: str, **detail: object) -> None:
    JOBS.mkdir(exist_ok=True)
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event": event,
        **detail,
    }
    with (JOBS / "preirt-panel-monitor.jsonl").open("a") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def has_tool_evidence(job: Path) -> bool:
    trajectories = list(job.glob("*/agent/trajectory.json"))
    return bool(trajectories) and any("bash_command" in path.read_text(errors="ignore") for path in trajectories)


def smoke_healthy(job: Path) -> bool:
    return job_scored_complete(job, 1) and has_tool_evidence(job)


def run_job(row: dict[str, str], tasks: list[str], attempts: int, phase: str, token: str) -> None:
    deployment = row["deployment"]
    job_name = f"preirt-{phase}-{deployment}"
    job = JOBS / job_name
    expected = len(tasks) * attempts
    if job_scored_complete(job, expected):
        note("skip_complete", deployment=deployment, phase=phase, trials=expected)
        return
    if row["provider"] == "openrouter" and campaign_cost() >= BUDGET_USD:
        raise RuntimeError(f"OpenRouter campaign cost reached ${BUDGET_USD:.2f}")

    env = os.environ.copy()
    if row["provider"] == "einfra":
        env["OPENAI_API_KEY"] = token
    else:
        # OpenRouter is OpenAI-compatible. LiteLLM routes model IDs whose vendor
        # namespace is `openai/` through this variable even with an
        # `openrouter/` provider prefix.
        env["OPENAI_API_KEY"] = token
        env["OPENROUTER_API_KEY"] = token
    task_args = [value for task in tasks for value in ("--include-task-name", task)]
    cooldowns = (900, 1800, 3600, 3600, 3600)
    for attempt_index, cooldown in enumerate(cooldowns, start=1):
        if job.exists() and (job / "result.json").exists():
            command = ["harbor", "job", "resume", "--job-path", str(job)]
            error_types = {
                (record["error"] or {}).get("exception_type")
                for record in trial_records(job)
                if record["error"]
            }
            for error_type in sorted(value for value in error_types if value):
                command += ["--filter-error-type", error_type]
        else:
            command = [
                "harbor", "run", "--path", "tasks/", "--agent", "terminus-2",
                "-m", row["model_id"], "--no-delete", "-n", "1", "-k", str(attempts),
                "--timeout-multiplier", "1.5", "--job-name", job_name,
                "--jobs-dir", "jobs", "-y", "--artifact", "/tmp/terminus2",
            ]
            if phase == "smoke":
                smoke_multiplier = "1.0" if row["provider"] == "einfra" else "0.25"
                command += ["--agent-timeout-multiplier", smoke_multiplier]
            if row["provider"] == "einfra":
                command += ["--ak", f"api_base={EINFRA_BASE}/"]
            command += task_args
        note("start", deployment=deployment, phase=phase, attempt=attempt_index, tasks=len(tasks))
        with (JOBS / f"{job_name}.log").open("a") as log:
            subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=False)
        if job_scored_complete(job, expected):
            scored = sum(record["reward"] is not None for record in trial_records(job))
            note("complete", deployment=deployment, phase=phase, trials=expected, scored=scored)
            if row["provider"] == "openrouter":
                note("cost", deployment=deployment, cumulative_usd=campaign_cost())
            return
        log_text = (JOBS / f"{job_name}.log").read_text(errors="ignore")[-100_000:]
        if "401" in log_text or "403" in log_text:
            raise RuntimeError(f"authentication failure in {job_name}")
        note("cooldown", deployment=deployment, seconds=cooldown)
        time.sleep(cooldown)
    raise RuntimeError(f"{job_name} remained incomplete after bounded recovery")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=("openrouter", "einfra"), required=True)
    parser.add_argument("--phase", choices=("smoke", "k1", "followup"), default="k1")
    parser.add_argument("--only", help="comma-separated deployment IDs")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    if (JOBS / ".preirt-paused").exists():
        raise RuntimeError(
            "pre-IRT campaign is paused; resume with: bash scripts/preirt_control.sh resume"
        )

    frozen_tasks = assert_frozen_tasks()
    panel = [row for row in load_panel() if row["provider"] == args.provider]
    if args.only:
        selected = set(args.only.split(","))
        panel = [row for row in panel if row["deployment"] in selected]
    token = provider_token(args.provider)
    available = live_model_ids(args.provider, token)
    missing = [api_model_id(row) for row in panel if api_model_id(row) not in available]
    if missing:
        raise RuntimeError(f"configured models unavailable from {args.provider}: {missing}")
    print(f"validated {len(panel)} {args.provider} deployments")
    if args.validate_only:
        return 0

    followups = assignments()
    for row in panel:
        if args.phase == "smoke":
            run_job(row, ["flagstat-report"], 1, "smoke", token)
            if not smoke_healthy(JOBS / f"preirt-smoke-{row['deployment']}"):
                raise RuntimeError(f"smoke is unscored or lacks tool evidence: {row['deployment']}")
        elif args.phase == "k1":
            smoke = JOBS / f"preirt-smoke-{row['deployment']}"
            if not smoke_healthy(smoke):
                run_job(row, ["flagstat-report"], 1, "smoke", token)
                if not smoke_healthy(smoke):
                    raise RuntimeError(f"smoke is unscored or lacks tool evidence: {row['deployment']}")
            run_job(row, frozen_tasks, 1, "k1", token)
        else:
            tasks = sorted(set(followups.get(row["deployment"], [])))
            if tasks:
                run_job(row, tasks, 2, "followup", token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
