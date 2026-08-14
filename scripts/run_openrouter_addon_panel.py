"""Run the August 2026 OpenRouter add-on panel on hard-8 and core-25."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

try:
    from scripts.einfra_panel_common import smoke_protocol_failures
except ModuleNotFoundError:  # Direct execution adds scripts/, not the repository root.
    from einfra_panel_common import smoke_protocol_failures

ROOT = Path(__file__).resolve().parent.parent
SMOKE_TASKS = ["gtf-to-bed", "vcf-trio-compound-het"]
TRANSIENT = ("429", "rate limit", "timed out", "timeouterror", "http 500", "http 502", "http 503", "http 504")
AUTH = ("http 401", "http 403", "unauthorized", "forbidden", "invalid api key")
COOLDOWN_SECONDS = (15 * 60, 30 * 60, 60 * 60)


def now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def read_lines(path: Path) -> list[str]:
    return [x.strip() for x in path.read_text().splitlines() if x.strip() and not x.lstrip().startswith("#")]


def read_models(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def job_complete(path: Path, expected: int) -> bool:
    result = path / "result.json"
    if not result.exists():
        return False
    data = json.loads(result.read_text())
    return bool(data.get("finished_at")) and data.get("stats", {}).get("n_trials") == expected


def completed_trials(path: Path) -> int:
    return len(list(path.glob("*/result.json")))


def validate_ids(models: list[dict[str, str]], token: str) -> None:
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/models", headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        available = {row["id"] for row in json.load(response)["data"]}
    missing = [row["model_id"] for row in models if row["model_id"] not in available]
    if missing:
        raise RuntimeError(f"exact OpenRouter model IDs unavailable: {', '.join(missing)}")


def append_jsonl(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def run_job(
    *, model: dict[str, str], scope: str, tasks: list[str], attempts: int,
    jobs_dir: Path, monitor: Path, concurrency: int,
) -> tuple[str, list[str]]:
    slug = model["slug"]
    job_name = f"openrouter-addon-{scope}-k{attempts}-{slug}"
    job = jobs_dir / job_name
    expected = len(tasks) * attempts
    if job_complete(job, expected):
        return "complete", []
    if job.exists() and (job / "result.json").exists():
        cmd = ["harbor", "job", "resume", "--job-path", str(job)]
    else:
        cmd = [
            "harbor", "run", "--path", "tasks/", "--agent", "terminus-2",
            "-m", f"openrouter/{model['model_id']}", "--no-delete", "-n", str(concurrency),
            "-k", str(attempts), "--timeout-multiplier", "1.5", "--job-name", job_name,
            "--jobs-dir", str(jobs_dir), "-y", "--artifact", "/tmp/terminus2",
        ]
        for task in tasks:
            cmd.extend(["--include-task-name", task])
    log_path = jobs_dir / f"{job_name}.log"
    log_offset = log_path.stat().st_size if log_path.exists() else 0
    append_jsonl(monitor, {"timestamp": now(), "event": "start", "job": job_name, "model": model["model_id"], "scope": scope, "completed": completed_trials(job), "expected": expected, "concurrency": concurrency})
    with log_path.open("a") as log:
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, env=os.environ.copy())
        while proc.poll() is None:
            try:
                proc.wait(timeout=900)
            except subprocess.TimeoutExpired:
                append_jsonl(monitor, {"timestamp": now(), "event": "interval", "job": job_name, "model": model["model_id"], "scope": scope, "completed": completed_trials(job), "expected": expected, "concurrency": concurrency})
    text = log_path.read_bytes()[log_offset:].decode(errors="replace").lower()[-200_000:]
    signals = [x for x in AUTH if x in text] + [x for x in TRANSIENT if x in text]
    state = "complete" if job_complete(job, expected) else "incomplete"
    append_jsonl(monitor, {"timestamp": now(), "event": f"exit:{proc.returncode}", "job": job_name, "model": model["model_id"], "scope": scope, "completed": completed_trials(job), "expected": expected, "state": state, "signals": signals})
    return state, signals


def run_job_with_recovery(
    *,
    model: dict[str, str],
    scope: str,
    tasks: list[str],
    attempts: int,
    jobs_dir: Path,
    monitor: Path,
    concurrency: int,
) -> tuple[str, list[str]]:
    """Resume transiently failed jobs after bounded 15/30/60 minute cooldowns."""
    last_state = "incomplete"
    last_signals: list[str] = []
    for attempt in range(len(COOLDOWN_SECONDS) + 1):
        last_state, last_signals = run_job(
            model=model,
            scope=scope,
            tasks=tasks,
            attempts=attempts,
            jobs_dir=jobs_dir,
            monitor=monitor,
            concurrency=concurrency,
        )
        if any(marker in last_signals for marker in AUTH):
            raise RuntimeError("OpenRouter authentication failed; renew OPENROUTER_API_KEY")
        if last_state == "complete" or not last_signals or attempt == len(COOLDOWN_SECONDS):
            return last_state, last_signals
        delay = COOLDOWN_SECONDS[attempt]
        append_jsonl(
            monitor,
            {
                "timestamp": now(),
                "event": "cooldown",
                "job": f"openrouter-addon-{scope}-k{attempts}-{model['slug']}",
                "model": model["model_id"],
                "scope": scope,
                "delay_seconds": delay,
                "signals": last_signals,
                "concurrency": 1,
            },
        )
        time.sleep(delay)
    return last_state, last_signals


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("configs/openrouter_addon_models.tsv"))
    parser.add_argument("--hard-tasks", type=Path, default=Path("configs/v2_retained_tasks.txt"))
    parser.add_argument("--core-tasks", type=Path, default=Path("configs/core25_tasks.txt"))
    parser.add_argument("--jobs-dir", type=Path, default=Path("jobs"))
    parser.add_argument("--monitor", type=Path, default=Path("jobs/openrouter-addon-monitor.jsonl"))
    parser.add_argument("--status", type=Path, default=Path("jobs/openrouter-addon-status.json"))
    parser.add_argument("--only-models", default="")
    parser.add_argument("--start-from", default="")
    parser.add_argument("--phase", choices=("both", "hard8", "core25", "smoke"), default="both")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    token = os.environ.get("OPENROUTER_API_KEY")
    if not token:
        raise RuntimeError("OPENROUTER_API_KEY is required")
    models = read_models(args.manifest)
    wanted = {x for x in args.only_models.split(",") if x}
    if wanted:
        models = [m for m in models if m["slug"] in wanted]
    if args.start_from:
        slugs = [m["slug"] for m in models]
        models = models[slugs.index(args.start_from):]
    validate_ids(models, token)
    print(f"Validated {len(models)} exact OpenRouter model IDs.")
    if args.validate_only:
        return 0
    phases = []
    if args.phase in ("both", "hard8"):
        phases.append(("hard8", read_lines(args.hard_tasks), 4))
    if args.phase in ("both", "core25"):
        phases.append(("core25", read_lines(args.core_tasks), 4))
    status: dict[str, object] = {"started_at": now(), "models": [m["slug"] for m in models], "results": []}
    for model in models:
        smoke_state, smoke_signals = run_job_with_recovery(model=model, scope="smoke", tasks=SMOKE_TASKS, attempts=1, jobs_dir=args.jobs_dir, monitor=args.monitor, concurrency=1)
        if smoke_state != "complete":
            status["results"].append({"model": model["slug"], "scope": "smoke", "status": smoke_state, "signals": smoke_signals})
            args.status.write_text(json.dumps(status, indent=2) + "\n")
            continue
        smoke_job = args.jobs_dir / f"openrouter-addon-smoke-k1-{model['slug']}"
        protocol_failures = smoke_protocol_failures(smoke_job)
        # Match the e-INFRA runner: a model counts as protocol-incompatible only
        # when *every* smoke trial lacks parsed tool-call evidence. A single
        # timed-out trial is an infrastructure error, not an incompatibility.
        if protocol_failures >= len(SMOKE_TASKS):
            status["results"].append(
                {
                    "model": model["slug"],
                    "scope": "smoke",
                    "status": "incompatible",
                    "protocol_failures": protocol_failures,
                }
            )
            append_jsonl(
                args.monitor,
                {
                    "timestamp": now(),
                    "event": "smoke-incompatible",
                    "job": smoke_job.name,
                    "model": model["model_id"],
                    "scope": "smoke",
                    "protocol_failures": protocol_failures,
                },
            )
            args.status.write_text(json.dumps(status, indent=2) + "\n")
            continue
        if args.phase == "smoke":
            status["results"].append({"model": model["slug"], "scope": "smoke", "status": "complete"})
            args.status.write_text(json.dumps(status, indent=2) + "\n")
            continue
        for scope, tasks, attempts in phases:
            state, signals = run_job_with_recovery(model=model, scope=scope, tasks=tasks, attempts=attempts, jobs_dir=args.jobs_dir, monitor=args.monitor, concurrency=1)
            status["results"].append({"model": model["slug"], "scope": scope, "status": state, "signals": signals})
            args.status.write_text(json.dumps(status, indent=2) + "\n")
            if state != "complete":
                break
    status["finished_at"] = now()
    args.status.write_text(json.dumps(status, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
