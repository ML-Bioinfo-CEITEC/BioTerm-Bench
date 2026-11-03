"""Shared integrity, discovery, and receipt helpers for the v1 model panel."""

from __future__ import annotations

import csv
import json
import os
import urllib.request
from pathlib import Path
from typing import Any

from preirt_common import trial_records

ROOT = Path(__file__).resolve().parents[1]
JOBS = ROOT / "jobs"
PANEL = ROOT / "configs" / "v1_model_panel.tsv"
TASK_TABLE = ROOT / "configs" / "benchmark_v1.0_tasks.tsv"
FREEZE_MANIFEST = ROOT / "configs" / "benchmark_v1.0_manifest.json"
PAUSE_MARKER = JOBS / ".v1-panel-paused"
MONITOR = JOBS / "v1-panel-monitor.jsonl"
EINFRA_BASE = "https://llm.ai.e-infra.cz/v1"

PANEL_FIELDS = (
    "deployment",
    "provider",
    "model_id",
    "api_model_id",
    "display_name",
    "api_base",
    "provenance",
    "added_at",
    "notes",
)


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
        value = os.environ.get("OPENROUTER_API_KEY") or dotenv_value("OPENROUTER_API_KEY")
    elif provider == "einfra":
        value = (
            os.environ.get("EINFRA_AI_TOKEN")
            or os.environ.get("E_INFRA_API_KEY")
            or dotenv_value("EINFRA_AI_TOKEN")
            or dotenv_value("E_INFRA_API_KEY")
        )
    else:
        return ""
    if not value:
        raise RuntimeError(f"credential for {provider} is unavailable")
    return value


def fetch_model_rows(provider: str, token: str) -> list[dict[str, Any]]:
    url = "https://openrouter.ai/api/v1/models" if provider == "openrouter" else EINFRA_BASE + "/models"
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    return list(payload.get("data", []))


def live_model_ids(provider: str, token: str) -> set[str]:
    return {str(row["id"]) for row in fetch_model_rows(provider, token)}


def load_panel() -> list[dict[str, str]]:
    if not PANEL.exists():
        raise RuntimeError(f"v1 panel is missing: {PANEL}")
    with PANEL.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows or tuple(rows[0]) != PANEL_FIELDS:
        raise RuntimeError("unexpected v1 panel schema")
    deployments = [row["deployment"] for row in rows]
    identities = [(row["provider"], row["api_model_id"]) for row in rows]
    if len(deployments) != len(set(deployments)) or len(identities) != len(set(identities)):
        raise RuntimeError("v1 panel contains duplicate deployment or provider/model identity")
    return rows


def source_tasks() -> list[str]:
    with TASK_TABLE.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    tasks = [row["source_task"] for row in rows]
    if len(tasks) != 50 or len(set(tasks)) != 50:
        raise RuntimeError("frozen v1 task table must contain 50 unique source tasks")
    return tasks


def freeze_digest() -> str:
    manifest = json.loads(FREEZE_MANIFEST.read_text())
    if manifest.get("version") != "1.0.0" or manifest.get("status") != "frozen":
        raise RuntimeError("BioTerm-Bench v1.0 is not frozen")
    return str(manifest["task_set_digest"])


def job_name(deployment: str, attempt: int) -> str:
    if attempt < 1 or attempt > 5:
        raise ValueError("attempt wave must be in 1..5")
    return f"v1-{deployment}-a{attempt}"


def job_scored_complete(path: Path, expected: int = 50) -> bool:
    result = path / "result.json"
    if not result.exists():
        return False
    try:
        root = json.loads(result.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    rows = trial_records(path)
    return (
        bool(root.get("finished_at"))
        and root.get("stats", {}).get("n_trials") == expected
        and len(rows) == expected
        and all(row["reward"] is not None for row in rows)
    )


def job_counts(path: Path) -> tuple[int, int, int]:
    rows = trial_records(path) if path.exists() else []
    scored = [row for row in rows if row["reward"] is not None]
    return len(scored), len(rows) - len(scored), sum(float(row["reward"]) > 0 for row in scored)


def openrouter_campaign_cost() -> float:
    total = 0.0
    for path in JOBS.glob("v1-or-*-a*"):
        if path.is_dir():
            total += sum(float(row["cost_usd"]) for row in trial_records(path))
    return total


def append_event(event: str, **details: object) -> None:
    from datetime import UTC, datetime

    JOBS.mkdir(exist_ok=True)
    with MONITOR.open("a") as handle:
        handle.write(
            json.dumps(
                {"timestamp": datetime.now(UTC).isoformat(), "event": event, **details},
                sort_keys=True,
            )
            + "\n"
        )
