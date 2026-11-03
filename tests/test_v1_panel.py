import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import v1_panel_common as common


def test_initial_panel_contains_all_intended_provider_models():
    rows = common.load_panel()
    by_provider = {}
    for row in rows:
        by_provider.setdefault(row["provider"], []).append(row)
    # The panel is append-only; later discovery may expand the initial inventory.
    assert len(by_provider["einfra"]) >= 12
    assert len(by_provider["openrouter"]) >= 35
    assert not by_provider.get("local")
    assert len({row["deployment"] for row in rows}) == len(rows)


def test_einfra_classifier_excludes_routes_and_modalities(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    from sync_v1_model_panel import is_einfra_concrete_chat

    assert is_einfra_concrete_chat("qwen3.8-27b")
    assert is_einfra_concrete_chat("deepseek-v4-flash-thinking")
    assert not is_einfra_concrete_chat("auto-llm")
    assert not is_einfra_concrete_chat("qwen3-embedding-4b")
    assert not is_einfra_concrete_chat("multilingual-e5-large-instruct")
    assert not is_einfra_concrete_chat("whisper-large-v3")


def test_attempt_waves_are_independent_and_bounded():
    assert common.job_name("ei-gemma4", 1) == "v1-ei-gemma4-a1"
    assert common.job_name("ei-gemma4", 5) == "v1-ei-gemma4-a5"
    with pytest.raises(ValueError):
        common.job_name("ei-gemma4", 6)


def test_start_command_uses_exact_frozen_tasks(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    from run_v1_panel import start_command

    with (ROOT / "configs" / "v1_model_panel.tsv").open(newline="") as handle:
        row = next(csv.DictReader(handle, delimiter="\t"))
    tasks = common.source_tasks()
    command = start_command(row, tasks, job="v1-test-a1", concurrency=1)
    assert command[command.index("-k") + 1] == "1"
    assert command[command.index("-n") + 1] == "1"
    assert command.count("--include-task-name") == 50
    included = {
        command[index + 1]
        for index, value in enumerate(command)
        if value == "--include-task-name"
    }
    assert included == set(tasks)


def test_frozen_task_identity_is_available():
    assert len(common.source_tasks()) == 50
    assert len(common.freeze_digest()) == 64
