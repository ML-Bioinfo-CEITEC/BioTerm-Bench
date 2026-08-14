from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_openrouter_addon_panel", ROOT / "scripts/run_openrouter_addon_panel.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_addon_manifest_has_exact_requested_models() -> None:
    rows = MODULE.read_models(ROOT / "configs/openrouter_addon_models.tsv")
    assert [row["model_id"] for row in rows] == [
        "nvidia/nemotron-3.5-lightning",
        "thinkingmachines/inkling-small",
        "meta/muse-glimmer-30b",
        "qwen/qwen3.6-35b-a3b",
        "openai/gpt-5.6-luna",
    ]


def test_core_and_hard_task_scopes_are_disjoint_and_complete() -> None:
    core = MODULE.read_lines(ROOT / "configs/core25_tasks.txt")
    hard = MODULE.read_lines(ROOT / "configs/v2_retained_tasks.txt")
    assert len(core) == 25
    assert len(hard) == 8
    assert set(core).isdisjoint(hard)
    assert all((ROOT / "tasks" / task).is_dir() for task in core + hard)


def test_complete_job_requires_finished_exact_trial_count(tmp_path: Path) -> None:
    job = tmp_path / "job"
    job.mkdir()
    (job / "result.json").write_text(
        '{"finished_at":"2026-08-12T00:00:00Z","stats":{"n_trials":32}}'
    )
    assert MODULE.job_complete(job, 32)
    assert not MODULE.job_complete(job, 100)


def test_openrouter_runner_reuses_terminal_protocol_smoke_gate() -> None:
    assert MODULE.smoke_protocol_failures.__module__.endswith("einfra_panel_common")


def test_transient_failures_cool_down_then_resume(monkeypatch, tmp_path: Path) -> None:
    outcomes = iter([("incomplete", ["429"]), ("complete", [])])
    sleeps: list[int] = []
    monkeypatch.setattr(MODULE, "run_job", lambda **kwargs: next(outcomes))
    monkeypatch.setattr(MODULE.time, "sleep", sleeps.append)

    state, signals = MODULE.run_job_with_recovery(
        model={"slug": "model", "model_id": "vendor/model"},
        scope="hard8",
        tasks=["task"],
        attempts=4,
        jobs_dir=tmp_path,
        monitor=tmp_path / "monitor.jsonl",
        concurrency=1,
    )

    assert (state, signals) == ("complete", [])
    assert sleeps == [900]


def test_auth_failure_stops_without_cooldown(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(MODULE, "run_job", lambda **kwargs: ("incomplete", ["http 401"]))
    monkeypatch.setattr(MODULE.time, "sleep", lambda delay: (_ for _ in ()).throw(AssertionError))

    try:
        MODULE.run_job_with_recovery(
            model={"slug": "model", "model_id": "vendor/model"},
            scope="smoke",
            tasks=["task"],
            attempts=1,
            jobs_dir=tmp_path,
            monitor=tmp_path / "monitor.jsonl",
            concurrency=1,
        )
    except RuntimeError as exc:
        assert "authentication failed" in str(exc)
    else:
        raise AssertionError("authentication failure was not raised")
