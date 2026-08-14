#!/usr/bin/env python3
"""Shared helpers for the e-INFRA Harbor runner and monitor."""

from __future__ import annotations

import csv
import json
import math
import os
import queue
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = "https://llm.ai.e-infra.cz/v1/"
DEFAULT_MODELS_URL = f"{DEFAULT_BASE_URL}models"
DEFAULT_STATUS_URL = "https://llm.ai.e-infra.cz/status/"
DEFAULT_STATUS_API_URL = "https://llm.ai.e-infra.cz/status/api/v1/models"
DEFAULT_DOCS_URL = "https://docs.cerit.io/en/docs/ai-as-a-service/chat-ai"
DEFAULT_MONITOR_PATH = Path("jobs/einfra-panel-monitor.jsonl")
DEFAULT_SNAPSHOT_ROOT = Path("jobs/einfra-snapshots")
DEFAULT_ATTEMPTS = 4
DEFAULT_TIMEOUT_MULTIPLIER = 1.5
DEFAULT_RETAINED_TASK_LIST = Path("configs/v2_retained_tasks.txt")
DEFAULT_SELECTION_RECEIPT = Path("notes/v2_task_selection.json")
SMOKE_TASKS = [
    "gtf-to-bed",
    "vcf-trio-compound-het",
    "rnaseq-featurecounts-matrix",
]
SMOKE_JOB_PREFIX = "einfra-smoke"
FULL_JOB_PREFIX = "einfra-k4"
# Ceiling agreed with the e-INFRA operators. Briefly set to 4 on 2026-08-13 and
# reverted the same hour before any job started under it, so no stored receipt
# ran above 2. Local hardware is not the binding constraint -- a trial container
# measures ~20-55 MiB against its 4 GB limit at ~0% CPU, since trials are
# API-bound -- the provider agreement is.
MAX_CONCURRENCY = 2
#: Concurrency a fresh panel run starts at.
PANEL_INITIAL_CONCURRENCY = 2
#: Floor the panel throttles *down* to when a provider signal appears. Kept at
#: 1 deliberately: it is the safety response, not the starting point, and must
#: stay below PANEL_INITIAL_CONCURRENCY for backing off to mean anything.
PANEL_START_CONCURRENCY = 1
CALIBRATION_SUCCESS_TRIALS = 20
CHECKPOINT_INTERVAL_SECONDS = 15 * 60
QUEUE_PERSISTENCE_SECONDS = 15 * 60
STALL_SECONDS = 30 * 60
MODEL_RETRY_SECONDS = 60 * 60
MODEL_RETRY_POLL_SECONDS = 15 * 60
DEFAULT_ARTIFACTS = ["/tmp/terminus2"]
TOKEN_ENV_NAME = "EINFRA_AI_TOKEN"

#: A bare status code is not evidence of a provider fault. ``job.log`` carries
#: agent output, so ordinary bioinformatics numbers -- read counts, coordinates,
#: lengths -- collide with 429/500/503, and Python tracebacks collide with 401.
#: Require an HTTP-ish preamble before a numeric code; the word forms below
#: still catch providers that phrase the error rather than number it.
_HTTP_CODE = r"(?:http[/ ]?[\d.]*\s+|status(?:\s*code)?\s*[:=]?\s*|error\s*code\s*[:=]?\s*|code\s*[:=]\s*)"

TRANSIENT_ERROR_PATTERNS = {
    "rate_limit": re.compile(
        rf"({_HTTP_CODE}429\b|rate.?limit|too many requests)", re.IGNORECASE
    ),
    "auth": re.compile(
        rf"({_HTTP_CODE}(401|403)\b|unauthorized|forbidden|invalid api key)", re.IGNORECASE
    ),
    # ``server\s*error`` (not ``server error``) so the CamelCase exception type
    # ``InternalServerError`` matches; litellm raises it for backend faults that
    # never carry an HTTP code, e.g. a broken vLLM proxy tunnel.
    "server": re.compile(
        rf"({_HTTP_CODE}(500|502|503|504)\b|server\s*error|bad\s*gateway|"
        r"service unavailable|can ?not write request body|connection refused)",
        re.IGNORECASE,
    ),
    # Do not match the word ``timeout`` alone: successful Harbor logs include
    # benign configuration such as ``--timeout-multiplier`` and LiteLLM emits
    # fallback timeout metadata.  Match only concrete failure wording/types.
    "timeout": re.compile(
        r"(timed out|deadline exceeded|AgentTimeoutError|TimeoutError)", re.IGNORECASE
    ),
    # "not found" alone matched agent-authored Python ("if not found_feature:")
    # echoed into the job log. Require the phrase to be about a model.
    "offline": re.compile(
        r"(model[^\n]{0,60}?(not found|unavailable|does not exist)|no such model|model_not_found)",
        re.IGNORECASE,
    ),
}

#: Python tracebacks carry ``File "...", line 401, in ...``. Those line numbers
#: collide with the bare HTTP codes above: "line 401" reads as an auth failure,
#: "line 429" as a rate limit, "line 500" as a server error. A single spurious
#: auth signal aborts the whole panel with a credential-renewal error, so strip
#: line references before classifying any text.
TRACEBACK_LINE_REF = re.compile(r"\bline\s+\d+", re.IGNORECASE)


def scrub_traceback_line_refs(text: str) -> str:
    return TRACEBACK_LINE_REF.sub(" ", text)


#: ``job.log`` interleaves harness output with everything the agent typed and
#: printed, so matching provider-fault words against the whole file is unsound.
#: Live false positives so far: ``line 401`` (traceback), ``if not
#: found_feature:`` (offline), and ``forbidden = {'X','Y','MT'}`` (auth) -- the
#: last is an entirely natural variable name for excluded chromosomes.
#: Only lines carrying a provider/transport marker are classified; genuine
#: faults in this harness always surface through one of them, and trial
#: ``exception_info`` is classified separately and structurally.
PROVIDER_LINE_MARKERS = (
    "litellm",
    "llm interaction",
    "openaiexception",
    "hosted_vllmexception",
    "apiconnectionerror",
    "apierror",
    "apistatuserror",
    "http/1.1",
    "http/2",
    # A bare "HTTP 429 ..." status line is provider output; agent code writes
    # "http://", never "http " followed by a status code.
    "http ",
)

#: Terminus-2 echoes the agent's keystrokes on these lines; never classify them.
AGENT_ECHO_MARKER = "sending keys:"


def provider_log_lines(text: str) -> str:
    """Keep only the lines of a job log that came from the provider layer."""
    kept = []
    for line in text.splitlines():
        lowered = line.lower()
        if AGENT_ECHO_MARKER in lowered:
            continue
        if any(marker in lowered for marker in PROVIDER_LINE_MARKERS):
            kept.append(line)
    return "\n".join(kept)


@dataclass(frozen=True)
class PanelEntry:
    slug: str
    model_id: str
    display_name: str
    family: str
    total_params: str
    active_params: str
    context_tokens: str
    max_output_tokens: str
    quantization: str
    reasoning_mode: str
    provider: str
    status_source: str
    notes: str

    @property
    def bare_model_id(self) -> str:
        return self.model_id.removeprefix("openai/")

    @property
    def smoke_job_name(self) -> str:
        return f"{SMOKE_JOB_PREFIX}-{self.slug}"

    @property
    def full_job_name(self) -> str:
        return f"{FULL_JOB_PREFIX}-{self.slug}"


@dataclass(frozen=True)
class JobStatus:
    state: str
    completed_trials: int
    expected_trials: int
    reward_trials: int
    error_trials: int
    finished_at: str | None


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso_now() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def parse_ts(value: str | None) -> datetime | None:
    """Parse a Harbor timestamp into an aware UTC datetime.

    Harbor writes job-level ``result.json`` timestamps as naive local time
    (``2026-08-12T20:57:35.860546``) but trial-level ones as ``Z``-suffixed UTC.
    Normalizing both here keeps ``summarize_progress`` from subtracting a naive
    datetime from an aware one, which raised ``TypeError`` on every interval
    checkpoint of a long job and on every ``start`` checkpoint of a resumed one.
    """
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone(UTC)


def ensure_token(env: dict[str, str] | None = None) -> str:
    source = env if env is not None else os.environ
    token = source.get(TOKEN_ENV_NAME)
    if not token:
        raise RuntimeError(f"{TOKEN_ENV_NAME} is required")
    return token


def read_manifest(path: Path) -> list[PanelEntry]:
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        rows = [
            PanelEntry(
                slug=row["slug"],
                model_id=row["model_id"],
                display_name=row["display_name"],
                family=row["family"],
                total_params=row["total_params"],
                active_params=row["active_params"],
                context_tokens=row["context_tokens"],
                max_output_tokens=row["max_output_tokens"],
                quantization=row["quantization"],
                reasoning_mode=row["reasoning_mode"],
                provider=row["provider"],
                status_source=row["status_source"],
                notes=row.get("notes", ""),
            )
            for row in reader
        ]
    if not rows:
        raise RuntimeError(f"Manifest has no rows: {path}")
    return rows


def filter_manifest(
    rows: list[PanelEntry],
    *,
    only_models: set[str] | None = None,
    start_from: str | None = None,
) -> list[PanelEntry]:
    filtered = [row for row in rows if not only_models or row.slug in only_models]
    if start_from:
        seen = False
        picked: list[PanelEntry] = []
        for row in filtered:
            if not seen and row.slug == start_from:
                seen = True
            if seen:
                picked.append(row)
        if not seen:
            raise RuntimeError(f"START_FROM slug not found after filtering: {start_from}")
        filtered = picked
    return filtered


def fetch_json(
    url: str,
    *,
    token: str | None = None,
    timeout: float = 30.0,
) -> Any:
    headers = {"User-Agent": "BioTerm-Bench/0.1"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def fetch_text(url: str, *, timeout: float = 30.0) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "BioTerm-Bench/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_model_ids(token: str, base_url: str = DEFAULT_BASE_URL) -> list[str]:
    payload = fetch_json(f"{base_url.rstrip('/')}/models", token=token)
    return [str(item.get("id")) for item in payload.get("data", []) if item.get("id")]


def validate_manifest_live(
    rows: list[PanelEntry], token: str, base_url: str = DEFAULT_BASE_URL
) -> tuple[list[str], list[str]]:
    available = set(fetch_model_ids(token, base_url))
    exact_ids = [row.bare_model_id for row in rows]
    missing = [model_id for model_id in exact_ids if model_id not in available]
    return exact_ids, missing


def snapshot_provider_state(
    *,
    manifest_path: Path,
    snapshot_root: Path = DEFAULT_SNAPSHOT_ROOT,
    token: str,
    base_url: str = DEFAULT_BASE_URL,
) -> Path:
    stamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    snapshot_dir = snapshot_root / stamp
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    (snapshot_dir / "manifest.tsv").write_text(manifest_path.read_text())
    harbor_version = "unknown"
    try:
        harbor_version = subprocess.run(
            ["harbor", "--version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    (snapshot_dir / "meta.json").write_text(
        json.dumps(
            {
                "retrieved_at": iso_now(),
                "base_url": base_url,
                "models_url": f"{base_url.rstrip('/')}/models",
                "status_url": DEFAULT_STATUS_URL,
                "docs_url": DEFAULT_DOCS_URL,
                "harbor_version": harbor_version,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    (snapshot_dir / "models.json").write_text(
        json.dumps(
            fetch_json(f"{base_url.rstrip('/')}/models", token=token), indent=2, sort_keys=True
        )
        + "\n"
    )
    try:
        (snapshot_dir / "status-models.json").write_text(
            json.dumps(fetch_json(DEFAULT_STATUS_API_URL), indent=2, sort_keys=True) + "\n"
        )
    except (OSError, urllib.error.URLError) as exc:
        (snapshot_dir / "status-models.json.error.txt").write_text(f"{type(exc).__name__}: {exc}\n")
    for target, name in (
        (DEFAULT_STATUS_URL, "status.html"),
        (DEFAULT_DOCS_URL, "docs-chat-ai.html"),
    ):
        try:
            (snapshot_dir / name).write_text(fetch_text(target))
        except urllib.error.URLError as exc:
            (snapshot_dir / f"{name}.error.txt").write_text(f"{type(exc).__name__}: {exc}\n")
    return snapshot_dir


def expected_trials(*, attempts: int, task_count: int) -> int:
    return attempts * task_count


def load_task_names(task_list: Path | None) -> list[str]:
    if task_list is None:
        return []
    names = [
        line.strip()
        for line in task_list.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    return names


def require_task_names(task_list: Path) -> list[str]:
    if not task_list.exists():
        raise RuntimeError(f"Retained task list is missing: {task_list}")
    names = load_task_names(task_list)
    if not names:
        raise RuntimeError(f"Retained task list is empty: {task_list}")
    return names


def require_selected_task_names(task_list: Path, receipt_path: Path) -> list[str]:
    """Require a complete probe receipt that exactly supports the retained list."""
    names = require_task_names(task_list)
    if not receipt_path.exists():
        raise RuntimeError(f"Task-selection receipt is missing: {receipt_path}")
    receipt = read_json(receipt_path)
    if not isinstance(receipt, list):
        raise TypeError(f"Task-selection receipt is not a list: {receipt_path}")
    if not receipt or not all(bool(row.get("attempts_complete")) for row in receipt):
        raise RuntimeError(f"Task-selection receipt contains incomplete probes: {receipt_path}")
    retained = [str(row.get("task")) for row in receipt if row.get("retained")]
    if retained != names:
        raise RuntimeError("Retained task list does not match task-selection receipt")
    return names


def build_agent_env(token: str) -> dict[str, str]:
    env = os.environ.copy()
    env.pop(TOKEN_ENV_NAME, None)
    env["OPENAI_API_KEY"] = token
    return env


def build_harbor_start_command(
    entry: PanelEntry,
    *,
    tasks_path: Path,
    jobs_dir: Path,
    job_name: str,
    attempts: int,
    concurrent_trials: int,
    task_names: list[str] | None = None,
    task_name: str | None = None,
    timeout_multiplier: float = DEFAULT_TIMEOUT_MULTIPLIER,
    api_base: str = DEFAULT_BASE_URL,
) -> list[str]:
    cmd = [
        "harbor",
        "run",
        "--path",
        str(tasks_path),
        "--agent",
        "terminus-2",
        "-m",
        entry.model_id,
        "--ak",
        f"api_base={api_base.rstrip('/')}/",
        "--no-delete",
        "-n",
        str(concurrent_trials),
        "-k",
        str(attempts),
        "--timeout-multiplier",
        str(timeout_multiplier),
        "--job-name",
        job_name,
        "--jobs-dir",
        str(jobs_dir),
        "-y",
    ]
    selected_tasks = list(task_names or [])
    if task_name:
        selected_tasks.append(task_name)
    for selected in selected_tasks:
        cmd.extend(["--include-task-name", selected])
    for artifact in DEFAULT_ARTIFACTS:
        cmd.extend(["--artifact", artifact])
    return cmd


def build_harbor_resume_command(job_dir: Path) -> list[str]:
    return ["harbor", "job", "resume", "--job-path", str(job_dir)]


def safe_command_for_log(cmd: list[str]) -> str:
    return " ".join(cmd)


def job_dir(jobs_dir: Path, job_name: str) -> Path:
    return jobs_dir / job_name


def job_log_path(job_path: Path) -> Path:
    return job_path / "job.log"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _stats_counts(payload: dict[str, Any]) -> tuple[int, int]:
    stats = payload.get("stats") or {}
    evals = stats.get("evals") or {}
    top_trials = int(stats.get("n_trials") or 0)
    top_errors = int(stats.get("n_errors") or 0)
    if not evals:
        return top_trials, top_errors
    nested_trials = 0
    nested_errors = 0
    for value in evals.values():
        value = value or {}
        trials = int(value.get("n_trials") or 0)
        errors = int(value.get("n_errors") or 0)
        # Harbor versions disagree on whether error-only trials are included in
        # n_trials. max() handles both conventions without double-counting.
        nested_trials += max(trials, errors)
        nested_errors += errors
    return max(top_trials, nested_trials), max(top_errors, nested_errors)


def read_job_status(job_path: Path, expected: int) -> JobStatus:
    result_path = job_path / "result.json"
    if not result_path.exists():
        return JobStatus("missing", 0, expected, 0, 0, None)
    data = read_json(result_path)
    completed_trials, nested_errors = _stats_counts(data)
    reward_trials = 0
    trial_error_count = 0
    for trial_result in job_path.glob("*/result.json"):
        trial = read_json(trial_result)
        rewards = (trial.get("verifier_result") or {}).get("rewards") or {}
        if rewards.get("reward") is not None:
            reward_trials += 1
        if trial.get("exception_info"):
            trial_error_count += 1
    error_trials = trial_error_count if any(job_path.glob("*/result.json")) else nested_errors
    finished_at = data.get("finished_at")
    if finished_at and completed_trials >= expected:
        state = "complete"
    elif finished_at:
        state = "finished_incomplete"
    else:
        state = "partial"
    return JobStatus(state, completed_trials, expected, reward_trials, error_trials, finished_at)


def tail_text(path: Path, *, max_bytes: int = 200_000) -> str:
    if not path.exists():
        return ""
    with path.open("rb") as fh:
        fh.seek(0, os.SEEK_END)
        size = fh.tell()
        fh.seek(max(0, size - max_bytes))
        return fh.read().decode("utf-8", errors="replace")


def text_from_offset(path: Path, start: int, *, max_bytes: int = 200_000) -> str:
    if not path.exists():
        return ""
    with path.open("rb") as fh:
        fh.seek(0, os.SEEK_END)
        size = fh.tell()
        fh.seek(max(start, size - max_bytes))
        return fh.read().decode("utf-8", errors="replace")


def classify_job_failures(
    job_path: Path,
    *,
    log_start_offset: int | None = None,
    trial_results: set[Path] | None = None,
) -> set[str]:
    signals: set[str] = set()
    log_path = job_log_path(job_path)
    text = provider_log_lines(
        scrub_traceback_line_refs(
            tail_text(log_path)
            if log_start_offset is None
            else text_from_offset(log_path, log_start_offset)
        )
    )
    for label, pattern in TRANSIENT_ERROR_PATTERNS.items():
        if pattern.search(text):
            signals.add(label)
    paths = trial_results if trial_results is not None else set(job_path.glob("*/result.json"))
    for trial_result in paths:
        trial = read_json(trial_result)
        exc = trial.get("exception_info") or {}
        # Classify the type and message only. The traceback is provenance, not
        # a provider signal, and scanning it produced false auth/rate-limit
        # hits from ordinary source-line references.
        exc_text = scrub_traceback_line_refs(
            " ".join(
                str(exc.get(field) or "")
                for field in ("exception_type", "exception_message")
            )
        )
        for label, pattern in TRANSIENT_ERROR_PATTERNS.items():
            if pattern.search(exc_text):
                signals.add(label)
    return signals


def summarize_progress(job_path: Path) -> dict[str, Any]:
    result_path = job_path / "result.json"
    if not result_path.exists():
        return {"n_trials": 0, "n_errors": 0, "last_progress_at": None}
    data = read_json(result_path)
    n_trials, n_errors = _stats_counts(data)
    started = parse_ts(data.get("started_at"))
    finished = parse_ts(data.get("finished_at"))
    now = utc_now()
    elapsed_s = None
    if started:
        elapsed_s = ((finished or now) - started).total_seconds()
    latest_trial_finished: datetime | None = None
    for trial_path in job_path.glob("*/result.json"):
        trial = read_json(trial_path)
        trial_finished = parse_ts(trial.get("finished_at"))
        if trial_finished and (
            latest_trial_finished is None or trial_finished > latest_trial_finished
        ):
            latest_trial_finished = trial_finished
    if latest_trial_finished is None:
        latest_trial_finished = finished or started
    return {
        "n_trials": n_trials,
        "n_errors": n_errors,
        "started_at": data.get("started_at"),
        "finished_at": data.get("finished_at"),
        "elapsed_s": elapsed_s,
        "last_progress_at": latest_trial_finished.isoformat().replace("+00:00", "Z")
        if latest_trial_finished
        else None,
    }


def estimate_eta(progress: dict[str, Any], expected: int) -> float | None:
    elapsed_s = progress.get("elapsed_s")
    completed = int(progress.get("n_trials") or 0)
    if not elapsed_s or completed <= 0 or completed >= expected:
        return None
    remaining = expected - completed
    rate = completed / elapsed_s
    if rate <= 0:
        return None
    return remaining / rate


def service_status(model_id: str) -> dict[str, Any]:
    """Return current public deployment state without exposing credentials."""
    lookup = model_id.removeprefix("openai/").lower()
    try:
        rows = fetch_json(DEFAULT_STATUS_API_URL)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return {"status": "unknown", "error": type(exc).__name__}
    for row in rows if isinstance(rows, list) else []:
        if str(row.get("model_name", "")).lower() != lookup:
            continue
        latest = row.get("latest") or {}
        return {
            "status": row.get("status") or "unknown",
            "requests_running": latest.get("num_requests_running"),
            "requests_waiting": latest.get("num_requests_waiting"),
            "last_seen": row.get("last_seen"),
        }
    return {"status": "not-listed"}


def append_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def monitor_payload(
    *,
    entry: PanelEntry,
    job_path: Path,
    expected: int,
    concurrent_trials: int,
    snapshot_dir: Path | None,
    event: str,
) -> dict[str, Any]:
    progress = summarize_progress(job_path)
    job_status = read_job_status(job_path, expected)
    latest_result = parse_ts(progress.get("last_progress_at"))
    eta_s = estimate_eta(progress, expected)
    stalled = False
    seconds_since_progress: float | None = None
    if latest_result and progress["n_trials"] < expected:
        seconds_since_progress = (utc_now() - latest_result).total_seconds()
        stalled = seconds_since_progress >= STALL_SECONDS
    provider_status = service_status(entry.bare_model_id)
    waiting = int(provider_status.get("requests_waiting") or 0)
    persistent_queue = bool(
        waiting > 0
        and progress["n_trials"] < expected
        and seconds_since_progress is not None
        and seconds_since_progress >= QUEUE_PERSISTENCE_SECONDS
    )
    failure_signals = classify_job_failures(job_path)
    if persistent_queue:
        failure_signals.add("queue")
    payload = {
        "timestamp": iso_now(),
        "event": event,
        "model_slug": entry.slug,
        "model_id": entry.model_id,
        "job_path": str(job_path),
        "completed_trials": progress["n_trials"],
        "expected_trials": expected,
        "error_trials": progress["n_errors"],
        "reward_trials": job_status.reward_trials,
        "job_state": job_status.state,
        "last_progress_at": latest_result.isoformat().replace("+00:00", "Z")
        if latest_result
        else None,
        "concurrency": concurrent_trials,
        "eta_seconds": round(eta_s, 2) if eta_s is not None else None,
        "stalled": stalled,
        "service_status": provider_status.get("status"),
        "service_requests_running": provider_status.get("requests_running"),
        "service_requests_waiting": provider_status.get("requests_waiting"),
        "service_last_seen": provider_status.get("last_seen"),
        "persistent_queue": persistent_queue,
        "failure_signals": sorted(failure_signals),
    }
    return payload


def run_subprocess(
    cmd: list[str],
    *,
    env: dict[str, str],
    log_path: Path,
    checkpoint_cb: callable[[], bool] | None = None,
    checkpoint_interval_seconds: float = CHECKPOINT_INTERVAL_SECONDS,
    poll_seconds: float = 0.25,
) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as log_fh:
        log_fh.write(f"$ {safe_command_for_log(cmd)}\n")
        log_fh.flush()
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        assert process.stdout is not None
        line_queue: queue.Queue[str | None] = queue.Queue()

        def _reader() -> None:
            assert process.stdout is not None
            for line in process.stdout:
                line_queue.put(line)
            line_queue.put(None)

        reader = threading.Thread(target=_reader, daemon=True)
        reader.start()
        last_checkpoint = time.monotonic()
        stream_closed = False
        while True:
            try:
                line = line_queue.get(timeout=poll_seconds)
            except queue.Empty:
                line = None
            if line is None:
                if stream_closed or process.poll() is not None:
                    break
            else:
                print(line, end="")
                log_fh.write(line)
                log_fh.flush()
            if checkpoint_cb and time.monotonic() - last_checkpoint >= checkpoint_interval_seconds:
                should_continue = checkpoint_cb()
                last_checkpoint = time.monotonic()
                if not should_continue:
                    process.terminate()
            if line is None and process.poll() is None:
                continue
            if line is None:
                stream_closed = True
        return int(process.returncode or 0)


def sleep_with_checkpoints(
    seconds: int, *, label: str, checkpoint_cb: callable[[], bool] | None = None
) -> None:
    deadline = time.monotonic() + seconds
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        if checkpoint_cb:
            should_continue = checkpoint_cb()
            if not should_continue:
                return
        time.sleep(min(remaining, CHECKPOINT_INTERVAL_SECONDS))


def ensure_model_available(
    *,
    entry: PanelEntry,
    token: str,
    base_url: str,
    retry_seconds: int = MODEL_RETRY_SECONDS,
    poll_seconds: int = MODEL_RETRY_POLL_SECONDS,
) -> bool:
    deadline = time.monotonic() + retry_seconds
    while True:
        ids = set(fetch_model_ids(token, base_url))
        if entry.bare_model_id in ids:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(poll_seconds)


def choose_next_concurrency(
    *,
    current: int,
    first_model_signals: set[str],
    completed_trials: int,
) -> int:
    # Throttling is checked first. A run already at the cap must still be able
    # to back off: testing ``current >= MAX_CONCURRENCY`` before the signals
    # made the safety response unreachable at exactly the concurrency where it
    # matters most.
    bad = {"rate_limit", "server", "timeout", "offline", "auth"} & first_model_signals
    if bad:
        return PANEL_START_CONCURRENCY
    if current >= MAX_CONCURRENCY:
        return current
    if completed_trials >= CALIBRATION_SUCCESS_TRIALS:
        return MAX_CONCURRENCY
    return current


def count_task_dirs(tasks_path: Path, task_names: list[str] | None = None) -> int:
    if task_names:
        return len(task_names)
    return len([child for child in tasks_path.iterdir() if child.is_dir()])


def smoke_protocol_failures(job_path: Path) -> int:
    """Count smoke trials that fail to demonstrate a parsed terminal tool call."""
    failures = 0
    for trial_result in job_path.glob("*/result.json"):
        trial = read_json(trial_result)
        # Match the exception *type* only. The traceback carries Harbor's own
        # install path (".../uv/tools/harbor/..."), so scanning the whole
        # payload made the bare marker "tool" fire on every raising trial --
        # a timeout was reported as a protocol incompatibility.
        exception_type = str((trial.get("exception_info") or {}).get("exception_type") or "").lower()
        explicit_protocol_failure = any(
            marker in exception_type for marker in ("protocol", "parse", "toolcall", "tool_call")
        )
        trial_dir = trial_result.parent
        trajectory_path = trial_dir / "agent" / "trajectory.json"
        tool_use_seen = False
        if trajectory_path.exists():
            try:
                trajectory = read_json(trajectory_path)
            except (json.JSONDecodeError, OSError):
                trajectory = {}
            tool_use_seen = any(
                step.get("source") == "agent"
                and any(
                    (call.get("function_name") or call.get("name")) == "bash_command"
                    for call in step.get("tool_calls") or []
                )
                for step in trajectory.get("steps") or []
            )
        if explicit_protocol_failure or not tool_use_seen:
            failures += 1
    return failures


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def confidence_interval(successes: int, total: int) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 0.0)
    p = successes / total
    z = 1.96
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))
