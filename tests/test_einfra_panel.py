from __future__ import annotations

import json
import re
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts import einfra_panel_common, run_einfra_panel
from scripts.einfra_panel_common import (
    DEFAULT_RETAINED_TASK_LIST,
    MAX_CONCURRENCY,
    PANEL_INITIAL_CONCURRENCY,
    PANEL_START_CONCURRENCY,
    SMOKE_TASKS,
    PanelEntry,
    build_agent_env,
    build_harbor_start_command,
    choose_next_concurrency,
    classify_job_failures,
    confidence_interval,
    filter_manifest,
    job_log_path,
    monitor_payload,
    read_job_status,
    read_manifest,
    require_selected_task_names,
    require_task_names,
    run_subprocess,
    service_status,
    smoke_protocol_failures,
    summarize_progress,
)


def _manifest_entry() -> PanelEntry:
    return PanelEntry(
        slug="gemma4",
        model_id="openai/gemma4",
        display_name="Gemma 4",
        family="google",
        total_params="31B",
        active_params="unknown",
        context_tokens="256000",
        max_output_tokens="32000",
        quantization="bf16",
        reasoning_mode="default",
        provider="einfra",
        status_source="https://docs.cerit.io/en/docs/ai-as-a-service/chat-ai",
        notes="",
    )


def test_manifest_order_and_exact_ids() -> None:
    rows = read_manifest(Path("configs/einfra_panel.tsv"))
    assert [row.slug for row in rows] == [
        "gemma4",
        "gpt-oss-120b",
        "mistral-medium-3.5",
        "qwen3.5-122b",
        "deepseek-v4-flash",
        "deepseek-v4-flash-thinking",
        "qwen3.5-int4",
        "glm-5.2",
        "kimi-k3",
    ]
    assert rows[0].model_id == "openai/gemma4"
    assert rows[-1].bare_model_id == "kimi-k3"
    assert all(row.active_params for row in rows)


def test_filter_manifest_only_and_start_from() -> None:
    rows = read_manifest(Path("configs/einfra_panel.tsv"))
    filtered = filter_manifest(
        rows, only_models={"gemma4", "glm-5.2", "kimi-k3"}, start_from="glm-5.2"
    )
    assert [row.slug for row in filtered] == ["glm-5.2", "kimi-k3"]


def test_harbor_command_uses_api_base_without_token() -> None:
    cmd = build_harbor_start_command(
        _manifest_entry(),
        tasks_path=Path("tasks"),
        jobs_dir=Path("jobs"),
        job_name="einfra-k4-gemma4",
        attempts=4,
        concurrent_trials=2,
        task_names=["gtf-to-bed", "vcf-to-tsv"],
        api_base="https://llm.ai.e-infra.cz/v1/",
    )
    joined = " ".join(cmd)
    assert "--ak api_base=https://llm.ai.e-infra.cz/v1/" in joined
    assert "Authorization" not in joined
    assert "EINFRA_AI_TOKEN" not in joined
    assert not any(part.startswith("sk-") for part in cmd)
    assert "--include-task-name gtf-to-bed" in joined
    assert "--include-task-name vcf-to-tsv" in joined


def test_harbor_child_env_receives_only_process_local_openai_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EINFRA_AI_TOKEN", "source-token")
    env = build_agent_env("source-token")
    assert env["OPENAI_API_KEY"] == "source-token"
    assert "EINFRA_AI_TOKEN" not in env


def test_repository_sources_contain_no_api_key_pattern() -> None:
    secret_pattern = re.compile(r"sk-[A-Za-z0-9]{16,}")
    roots = [
        Path("configs"),
        Path("docs"),
        Path("notes"),
        Path("paper"),
        Path("scripts"),
        Path("tests"),
    ]
    paths = [Path("README.md")]
    for root in roots:
        paths.extend(path for path in root.rglob("*") if path.is_file() and path.suffix != ".pdf")
    matches = [
        str(path) for path in paths if secret_pattern.search(path.read_text(errors="ignore"))
    ]
    assert matches == []


def test_job_status_uses_nested_evals_and_no_error_double_count(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "result.json").write_text(
        json.dumps(
            {
                "finished_at": "2026-08-12T12:00:00+00:00",
                "stats": {
                    "n_trials": 1,
                    "n_errors": 99,
                    "evals": {
                        "a": {"n_trials": 3, "n_errors": 1},
                        "b": {"n_trials": 5, "n_errors": 2},
                    },
                },
            }
        )
    )
    for idx, has_error in enumerate([False, True, True]):
        trial = job_dir / f"t{idx}"
        trial.mkdir()
        payload = {"verifier_result": {"rewards": {"reward": 1.0}}}
        if has_error:
            payload["exception_info"] = {"exception_type": "AgentTimeoutError"}
            payload["verifier_result"] = None
        (trial / "result.json").write_text(json.dumps(payload))
    status = read_job_status(job_dir, expected=8)
    assert status.state == "complete"
    assert status.completed_trials == 8
    assert status.error_trials == 2
    assert status.reward_trials == 1


def test_job_status_handles_harbor_error_only_and_top_level_counts(tmp_path: Path) -> None:
    error_only = tmp_path / "error-only"
    error_only.mkdir()
    (error_only / "result.json").write_text(
        json.dumps(
            {
                "stats": {
                    "evals": {"e": {"n_trials": 0, "n_errors": 2}},
                }
            }
        )
    )
    assert read_job_status(error_only, expected=8).completed_trials == 2

    complete = tmp_path / "complete"
    complete.mkdir()
    (complete / "result.json").write_text(
        json.dumps(
            {
                "finished_at": "2026-08-12T12:00:00+00:00",
                "stats": {
                    "n_trials": 100,
                    "n_errors": 8,
                    "evals": {"e": {"n_trials": 99, "n_errors": 8}},
                },
            }
        )
    )
    status = read_job_status(complete, expected=100)
    assert status.state == "complete"
    assert status.completed_trials == 100


def test_classify_job_failures_and_monitor_payload_use_internal_job_log(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        einfra_panel_common,
        "service_status",
        lambda _model_id: {
            "status": "online",
            "requests_running": 1,
            "requests_waiting": 0,
            "last_seen": "2026-08-12T12:10:00Z",
        },
    )
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    job_log_path(job_dir).write_text("HTTP 429 rate limit\nHTTP 503 service unavailable\n")
    (job_dir / "result.json").write_text(
        json.dumps(
            {
                "started_at": "2026-08-12T12:00:00+00:00",
                "stats": {"evals": {"e": {"n_trials": 4, "n_errors": 2}}},
            }
        )
    )
    trial = job_dir / "trial1"
    trial.mkdir()
    (trial / "result.json").write_text(
        json.dumps(
            {
                "finished_at": "2026-08-12T12:10:00+00:00",
                "exception_info": {"exception_type": "AgentTimeoutError"},
            }
        )
    )
    signals = classify_job_failures(job_dir)
    assert {"rate_limit", "server", "timeout"} <= signals

    payload = monitor_payload(
        entry=_manifest_entry(),
        job_path=job_dir,
        expected=16,
        concurrent_trials=1,
        snapshot_dir=None,
        event="interval",
    )
    assert payload["completed_trials"] == 4
    assert payload["expected_trials"] == 16
    assert payload["concurrency"] == 1
    assert payload["last_progress_at"] == "2026-08-12T12:10:00Z"
    assert "timeout" in payload["failure_signals"]
    assert payload["service_status"] == "online"
    assert payload["service_requests_waiting"] == 0


def test_failure_classification_can_ignore_pre_cooldown_history(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    old_trial = job_dir / "old"
    new_trial = job_dir / "new"
    old_trial.mkdir(parents=True)
    new_trial.mkdir()
    log_path = job_log_path(job_dir)
    log_path.write_text("HTTP 429 rate limit\n")
    offset = log_path.stat().st_size
    with log_path.open("a") as fh:
        fh.write("resumed successfully\n")
    (old_trial / "result.json").write_text(
        json.dumps({"exception_info": {"exception_type": "AgentTimeoutError"}})
    )
    new_result = new_trial / "result.json"
    new_result.write_text(
        json.dumps({"verifier_result": {"rewards": {"reward": 1.0}}})
    )
    assert classify_job_failures(
        job_dir, log_start_offset=offset, trial_results={new_result}
    ) == set()


def test_failure_classification_ignores_timeout_configuration_text(
    tmp_path: Path,
) -> None:
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    job_log_path(job_dir).write_text(
        "harbor run --timeout-multiplier 1.5\n"
        "Using request timeout: 180 seconds\n"
        "Job completed successfully\n"
    )
    assert classify_job_failures(job_dir) == set()


def test_failure_classification_covers_auth_offline_and_incomplete_result(
    tmp_path: Path,
) -> None:
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    job_log_path(job_dir).write_text("HTTP 401 unauthorized: model gemma4 unavailable\n")
    (job_dir / "result.json").write_text(
        json.dumps(
            {
                "finished_at": "2026-08-12T12:00:00+00:00",
                "stats": {"evals": {"e": {"n_trials": 1, "n_errors": 1}}},
            }
        )
    )
    assert {"auth", "offline"} <= classify_job_failures(job_dir)
    status = read_job_status(job_dir, expected=3)
    assert status.state == "finished_incomplete"
    assert status.completed_trials == 1


def test_monitor_marks_stalled_progress_and_records_service_queue(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        einfra_panel_common,
        "utc_now",
        lambda: datetime(2026, 8, 12, 12, 45, tzinfo=UTC),
    )
    monkeypatch.setattr(
        einfra_panel_common,
        "service_status",
        lambda _model_id: {
            "status": "online",
            "requests_running": 2,
            "requests_waiting": 4,
            "last_seen": "2026-08-12T12:44:00Z",
        },
    )
    job_dir = tmp_path / "job"
    trial_dir = job_dir / "trial"
    trial_dir.mkdir(parents=True)
    (job_dir / "result.json").write_text(
        json.dumps(
            {
                "started_at": "2026-08-12T12:00:00+00:00",
                "stats": {"evals": {"e": {"n_trials": 1, "n_errors": 0}}},
            }
        )
    )
    (trial_dir / "result.json").write_text(
        json.dumps(
            {
                "finished_at": "2026-08-12T12:10:00+00:00",
                "verifier_result": {"rewards": {"reward": 0.0}},
            }
        )
    )
    payload = monitor_payload(
        entry=_manifest_entry(),
        job_path=job_dir,
        expected=4,
        concurrent_trials=1,
        snapshot_dir=None,
        event="interval",
    )
    assert payload["stalled"] is True
    assert payload["service_requests_waiting"] == 4
    assert payload["persistent_queue"] is True
    assert "queue" in payload["failure_signals"]


def test_service_status_does_not_alias_thinking_deployment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        einfra_panel_common,
        "fetch_json",
        lambda _url: [
            {
                "model_name": "deepseek-v4-flash",
                "status": "online",
                "latest": {"num_requests_running": 1, "num_requests_waiting": 0},
            }
        ],
    )
    assert service_status("deepseek-v4-flash-thinking") == {"status": "not-listed"}


def test_smoke_protocol_failures_require_trajectory_tool_calls(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    for index in range(3):
        trial_dir = job_dir / f"trial-{index}"
        trajectory_dir = trial_dir / "agent"
        trajectory_dir.mkdir(parents=True)
        (trial_dir / "result.json").write_text(
            json.dumps({"verifier_result": {"rewards": {"reward": 0.0}}})
        )
        if index == 0:
            steps = [
                {"source": "agent", "tool_calls": [{"function_name": "bash_command"}]}
            ]
        elif index == 1:
            steps = [
                {"source": "agent", "tool_calls": [{"function_name": "mark_task_complete"}]}
            ]
        else:
            steps = []
        (trajectory_dir / "trajectory.json").write_text(json.dumps({"steps": steps}))
    assert smoke_protocol_failures(job_dir) == 2


def test_run_subprocess_fires_checkpoint_without_stdout(tmp_path: Path) -> None:
    marks: list[float] = []

    def _checkpoint() -> bool:
        marks.append(time.monotonic())
        return True

    log_path = tmp_path / "job.log"
    exit_code = run_subprocess(
        ["python3", "-c", "import time; time.sleep(0.35)"],
        env={},
        log_path=log_path,
        checkpoint_cb=_checkpoint,
        checkpoint_interval_seconds=0.1,
        poll_seconds=0.05,
    )
    assert exit_code == 0
    assert len(marks) >= 2
    assert "$ python3 -c import time; time.sleep(0.35)" in log_path.read_text()


def test_require_task_names_missing_or_empty(tmp_path: Path) -> None:
    missing = tmp_path / "missing.txt"
    with pytest.raises(RuntimeError, match="missing"):
        require_task_names(missing)

    empty = tmp_path / "empty.txt"
    empty.write_text("# comment only\n")
    with pytest.raises(RuntimeError, match="empty"):
        require_task_names(empty)


def test_full_task_list_requires_matching_complete_selection_receipt(tmp_path: Path) -> None:
    task_list = tmp_path / "tasks.txt"
    task_list.write_text("task-a\ntask-b\n")
    receipt = tmp_path / "receipt.json"
    with pytest.raises(RuntimeError, match="missing"):
        require_selected_task_names(task_list, receipt)

    receipt.write_text(
        json.dumps(
            [
                {"task": "task-a", "retained": True, "attempts_complete": True},
                {"task": "task-b", "retained": True, "attempts_complete": False},
            ]
        )
    )
    with pytest.raises(RuntimeError, match="incomplete"):
        require_selected_task_names(task_list, receipt)

    receipt.write_text(
        json.dumps(
            [
                {"task": "task-b", "retained": True, "attempts_complete": True},
                {"task": "task-a", "retained": True, "attempts_complete": True},
            ]
        )
    )
    with pytest.raises(RuntimeError, match="does not match"):
        require_selected_task_names(task_list, receipt)

    receipt.write_text(
        json.dumps(
            [
                {"task": "task-a", "retained": True, "attempts_complete": True},
                {"task": "task-b", "retained": True, "attempts_complete": True},
            ]
        )
    )
    assert require_selected_task_names(task_list, receipt) == ["task-a", "task-b"]


def test_smoke_command_has_three_representative_tasks() -> None:
    cmd = build_harbor_start_command(
        _manifest_entry(),
        tasks_path=Path("tasks"),
        jobs_dir=Path("jobs"),
        job_name="einfra-smoke-gemma4",
        attempts=1,
        concurrent_trials=1,
        task_names=SMOKE_TASKS,
        api_base="https://llm.ai.e-infra.cz/v1/",
    )
    joined = " ".join(cmd)
    for task in SMOKE_TASKS:
        assert f"--include-task-name {task}" in joined
    assert joined.count("--include-task-name") == 3


def test_smoke_only_runs_smoke_not_full(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    events: list[tuple[str, bool, tuple[str, ...]]] = []
    monkeypatch.setenv("EINFRA_AI_TOKEN", "test-token")
    monkeypatch.setattr(run_einfra_panel, "read_manifest", lambda _path: [_manifest_entry()])
    monkeypatch.setattr(run_einfra_panel, "filter_manifest", lambda rows, **_kwargs: rows)
    monkeypatch.setattr(
        run_einfra_panel,
        "validate_manifest_live",
        lambda rows, token, base_url: ([r.bare_model_id for r in rows], []),
    )
    monkeypatch.setattr(
        run_einfra_panel, "snapshot_provider_state", lambda **_kwargs: tmp_path / "snap"
    )
    monkeypatch.setattr(run_einfra_panel, "write_json", lambda _path, _payload: None)
    monkeypatch.setattr(run_einfra_panel, "append_checkpoint", lambda _path, _payload: None)

    def _run_one_job(**kwargs):
        events.append((kwargs["entry"].slug, kwargs["smoke"], tuple(kwargs["task_names"])))
        return ("complete", set(), len(kwargs["task_names"]))

    monkeypatch.setattr(run_einfra_panel, "run_one_job", _run_one_job)
    monkeypatch.setattr(
        run_einfra_panel.sys,
        "argv",
        ["run_einfra_panel.py", "--smoke", "--jobs-dir", str(tmp_path / "jobs")],
    )
    assert run_einfra_panel.main() == 0
    assert events == [("gemma4", True, tuple(SMOKE_TASKS))]


def test_retry_exhaustion_is_recorded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    statuses: list[dict] = []
    cooldowns: list[int] = []
    monkeypatch.setenv("EINFRA_AI_TOKEN", "test-token")
    monkeypatch.setattr(run_einfra_panel, "read_manifest", lambda _path: [_manifest_entry()])
    monkeypatch.setattr(run_einfra_panel, "filter_manifest", lambda rows, **_kwargs: rows)
    monkeypatch.setattr(
        run_einfra_panel,
        "validate_manifest_live",
        lambda rows, token, base_url: ([r.bare_model_id for r in rows], []),
    )
    monkeypatch.setattr(
        run_einfra_panel, "require_selected_task_names", lambda _tasks, _receipt: ["task-a"]
    )
    monkeypatch.setattr(
        run_einfra_panel, "snapshot_provider_state", lambda **_kwargs: tmp_path / "snap"
    )
    monkeypatch.setattr(run_einfra_panel, "append_checkpoint", lambda _path, _payload: None)
    monkeypatch.setattr(
        run_einfra_panel,
        "sleep_with_checkpoints",
        lambda seconds, **_kwargs: cooldowns.append(seconds),
    )
    monkeypatch.setattr(run_einfra_panel, "count_task_dirs", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr(
        run_einfra_panel,
        "write_json",
        lambda _path, payload: statuses.append(json.loads(json.dumps(payload))),
    )

    def _run_one_job(**kwargs):
        if kwargs["smoke"]:
            return ("complete", set(), 3)
        return ("failed", {"timeout"}, 0)

    monkeypatch.setattr(run_einfra_panel, "run_one_job", _run_one_job)
    monkeypatch.setattr(
        run_einfra_panel.sys,
        "argv",
        ["run_einfra_panel.py", "--jobs-dir", str(tmp_path / "jobs")],
    )
    assert run_einfra_panel.main() == 0
    assert any(
        result["status"] == "retries-exhausted"
        for result in statuses[-1]["results"]
    )
    assert cooldowns == [15 * 60, 30 * 60, 60 * 60]


def test_default_retained_task_list_exists_and_is_used() -> None:
    tasks = require_task_names(DEFAULT_RETAINED_TASK_LIST)
    assert tasks
    assert len(tasks) == 8


def test_next_concurrency_gates_on_clean_calibration() -> None:
    # Clean calibration promotes straight to the cap.
    assert (
        choose_next_concurrency(current=1, first_model_signals=set(), completed_trials=20)
        == MAX_CONCURRENCY
    )
    # Any provider signal throttles to the floor, which must stay below both the
    # cap and the initial concurrency or backing off would be a no-op.
    assert (
        choose_next_concurrency(current=1, first_model_signals={"rate_limit"}, completed_trials=25)
        == PANEL_START_CONCURRENCY
    )
    assert PANEL_START_CONCURRENCY < PANEL_INITIAL_CONCURRENCY <= MAX_CONCURRENCY
    # Already at the cap: stay put rather than climbing further.
    assert (
        choose_next_concurrency(
            current=MAX_CONCURRENCY, first_model_signals=set(), completed_trials=40
        )
        == MAX_CONCURRENCY
    )
    # A signal must still throttle a run that is already at the cap. Checking
    # the cap first made this unreachable, so a 429 storm at max concurrency
    # would never have reduced load.
    assert (
        choose_next_concurrency(
            current=MAX_CONCURRENCY, first_model_signals={"server"}, completed_trials=40
        )
        == PANEL_START_CONCURRENCY
    )
    assert (
        choose_next_concurrency(
            current=MAX_CONCURRENCY, first_model_signals={"rate_limit"}, completed_trials=999
        )
        == PANEL_START_CONCURRENCY
    )


def test_confidence_interval_bounds() -> None:
    lo, hi = confidence_interval(19, 25)
    assert 0.0 <= lo <= hi <= 1.0


def test_progress_handles_naive_local_job_timestamps(tmp_path: Path) -> None:
    """Harbor writes job-level timestamps naive-local and trial-level UTC-aware.

    Mixing the two used to raise ``TypeError: can't subtract offset-naive and
    offset-aware datetimes`` inside ``summarize_progress``, which killed the
    panel on the first interval checkpoint of a 32-trial job and on the
    ``start`` checkpoint of any resumed job.
    """
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    started_local = datetime.now().astimezone().replace(tzinfo=None) - timedelta(minutes=30)
    (job_dir / "result.json").write_text(
        json.dumps(
            {
                "started_at": started_local.isoformat(),
                "stats": {"evals": {"e": {"n_trials": 4, "n_errors": 0}}},
            }
        )
    )
    trial = job_dir / "trial1"
    trial.mkdir()
    (trial / "result.json").write_text(
        json.dumps({"finished_at": "2026-08-12T12:10:00Z"})
    )

    progress = summarize_progress(job_dir)

    assert progress["n_trials"] == 4
    assert progress["last_progress_at"] == "2026-08-12T12:10:00Z"
    # ~30 minutes of elapsed wall clock, not a timezone-offset artifact.
    assert 1500 < progress["elapsed_s"] < 2100


def test_progress_elapsed_uses_finished_at_when_present(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "result.json").write_text(
        json.dumps(
            {
                "started_at": "2026-08-12T20:00:00",
                "finished_at": "2026-08-12T20:15:00",
                "stats": {"evals": {"e": {"n_trials": 8, "n_errors": 0}}},
            }
        )
    )

    progress = summarize_progress(job_dir)

    assert progress["elapsed_s"] == 900.0


def _write_smoke_trial(
    job_dir: Path, name: str, *, tool_calls: bool, exception_type: str | None
) -> None:
    trial = job_dir / name
    (trial / "agent").mkdir(parents=True)
    steps: list[dict[str, object]] = [{"source": "user"}]
    if tool_calls:
        steps.append(
            {
                "source": "agent",
                "tool_calls": [{"tool_call_id": "1", "function_name": "bash_command"}],
            }
        )
    (trial / "agent" / "trajectory.json").write_text(json.dumps({"steps": steps}))
    payload: dict[str, object] = {}
    if exception_type:
        payload["exception_info"] = {
            "exception_type": exception_type,
            "exception_message": "timed out",
            # Harbor tracebacks embed its own install path, which contains
            # the substring "tool" and used to trigger a false positive.
            "exception_traceback": (
                'File "/Users/x/.local/share/uv/tools/harbor/lib/python3.13/'
                'site-packages/harbor/agents/terminus_2/terminus_2.py", line 1605'
            ),
        }
    (trial / "result.json").write_text(json.dumps(payload))


def test_timeout_with_real_tool_calls_is_not_a_protocol_failure(tmp_path: Path) -> None:
    """A timed-out trial that made bash_command calls is an infra error.

    The Harbor traceback contains ".../uv/tools/harbor/...", so matching the
    bare marker "tool" against the whole exception payload flagged every
    raising trial as protocol-incompatible and discarded working models.
    """
    job_dir = tmp_path / "smoke"
    job_dir.mkdir()
    _write_smoke_trial(job_dir, "t1", tool_calls=True, exception_type="AgentTimeoutError")
    _write_smoke_trial(job_dir, "t2", tool_calls=True, exception_type=None)

    assert smoke_protocol_failures(job_dir) == 0


def test_missing_tool_calls_and_parse_exceptions_still_count(tmp_path: Path) -> None:
    job_dir = tmp_path / "smoke"
    job_dir.mkdir()
    _write_smoke_trial(job_dir, "t1", tool_calls=False, exception_type=None)
    _write_smoke_trial(job_dir, "t2", tool_calls=True, exception_type="ToolCallParseError")

    assert smoke_protocol_failures(job_dir) == 2


def test_traceback_line_numbers_do_not_forge_provider_signals(tmp_path: Path) -> None:
    """``line 401`` in a traceback must not read as an HTTP 401.

    A spurious auth signal aborts the entire panel with a credential-renewal
    error, and spurious 429/500 signals trigger hour-long cooldowns. Python
    tracebacks routinely reference those line numbers.
    """
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    job_log_path(job_dir).write_text(
        'File "/x/concurrent/futures/_base.py", line 401, in __get_result\n'
        'File "/x/harbor/agents/terminus_2.py", line 429, in run\n'
        'File "/x/harbor/cli.py", line 500, in main\n'
    )
    trial = job_dir / "trial1"
    trial.mkdir()
    (trial / "result.json").write_text(
        json.dumps(
            {
                "exception_info": {
                    "exception_type": "BadRequestError",
                    "exception_message": "vllm rejected <|channel|> tags in content",
                    "exception_traceback": (
                        'File "/x/_base.py", line 401, in __get_result\n'
                        'File "/x/pool.py", line 503, in submit'
                    ),
                }
            }
        )
    )

    assert classify_job_failures(job_dir) == set()


def test_genuine_auth_and_rate_limit_signals_still_detected(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    job_log_path(job_dir).write_text("HTTP 429 Too Many Requests\n")
    trial = job_dir / "trial1"
    trial.mkdir()
    (trial / "result.json").write_text(
        json.dumps(
            {
                "exception_info": {
                    "exception_type": "AuthenticationError",
                    "exception_message": "Error code: 401 - invalid api key",
                }
            }
        )
    )

    signals = classify_job_failures(job_dir)
    assert "auth" in signals
    assert "rate_limit" in signals


def test_agent_output_does_not_forge_provider_signals(tmp_path: Path) -> None:
    """``job.log`` carries agent output, which collides with bare code patterns.

    Observed live: the agent wrote ``if not found_feature:`` and the loose
    "not found" pattern reported the model as offline, which would defer the
    model to the revisit phase. Bioinformatics numbers collide the same way --
    a read count of 429 or a coordinate of 500 is not a provider fault.
    """
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    job_log_path(job_dir).write_text(
        "        if not found_feature:\n"
        "            unmapped_no_feature += 1\n"
        "reads passing filter: 429\n"
        "mean insert size 500, max 503\n"
        "chr1\t502\t504\tgene_a\n"
    )

    assert classify_job_failures(job_dir) == set()


def test_provider_worded_and_http_coded_failures_still_detected(tmp_path: Path) -> None:
    """Genuine faults reach the classifier by two paths.

    Provider-marked lines in ``job.log`` (litellm and HTTP status output), and
    structured ``exception_info`` on the trial. Agent-authored prose in the log
    is deliberately not a third path -- that is what produced the live false
    positives -- so each case below is tested through the path it really uses.
    """
    log_cases = [
        ("HTTP 429 Too Many Requests", "rate_limit"),
        ("litellm.RateLimitError: exceeded", "rate_limit"),
        ("Unknown Error in LLM interaction: litellm.APIStatusError: Error code: 503", "server"),
        ("litellm.APIError: 502 Bad Gateway", "server"),
        ("HTTP 403 forbidden", "auth"),
        ("litellm.NotFoundError: The model gpt-oss-120b is currently unavailable", "offline"),
    ]
    for text, expected in log_cases:
        job_dir = tmp_path / f"log-{expected}-{abs(hash(text))}"
        job_dir.mkdir()
        job_log_path(job_dir).write_text(text + "\n")
        assert expected in classify_job_failures(job_dir), text

    exception_cases = [
        ("APIConnectionError", "connection refused", "server"),
        ("NotFoundError", "no such model", "offline"),
        ("RateLimitError", "Error code: 429", "rate_limit"),
    ]
    for exc_type, message, expected in exception_cases:
        job_dir = tmp_path / f"exc-{expected}-{abs(hash(message))}"
        trial = job_dir / "t1"
        trial.mkdir(parents=True)
        (trial / "result.json").write_text(
            json.dumps({"exception_info": {"exception_type": exc_type, "exception_message": message}})
        )
        assert expected in classify_job_failures(job_dir), message


def test_backend_faults_without_http_codes_are_server_signals(tmp_path: Path) -> None:
    """litellm raises backend faults that carry no HTTP status code.

    Observed live on e-INFRA: every kimi-k3 trial failed with
    ``InternalServerError ... Can not write request body for
    http://frps-proxy-tunnel...``. The CamelCase type has no space, so a
    ``server error`` pattern missed it and the panel saw no reason to cool down.
    """
    for message in [
        (
            "litellm.InternalServerError: Hosted_vllmException - [Errno None] "
            "Can not write request body for http://frps-proxy-tunnel.vllm-ns.svc:8003/v1/chat/completions"
        ),
        "APIConnectionError: connection refused",
    ]:
        job_dir = tmp_path / f"job{abs(hash(message))}"
        trial = job_dir / "t1"
        trial.mkdir(parents=True)
        (trial / "result.json").write_text(
            json.dumps(
                {
                    "exception_info": {
                        "exception_type": "InternalServerError",
                        "exception_message": message,
                    }
                }
            )
        )
        assert "server" in classify_job_failures(job_dir), message
