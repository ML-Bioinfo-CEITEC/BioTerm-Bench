from pathlib import Path

import pytest

from scripts.select_v2_tasks import (
    Attempt,
    render_selection_table,
    require_candidate_count,
    require_probe_shape,
    select,
)


def test_selection_excludes_ceilings_floors_and_errors() -> None:
    attempts = [
        *(Attempt("mixed", reward, None) for reward in (1, 0, 1, 0, 1, 0)),
        *(Attempt("ceiling", 1, None) for _ in range(6)),
        *(Attempt("floor", 0, None) for _ in range(6)),
        Attempt("errored", None, "RateLimitError"),
        Attempt("errored", 1, None),
    ]
    retained, receipt = select(
        attempts,
        ["mixed", "ceiling", "floor", "errored"],
        minimum=0.1,
        maximum=0.8,
    )
    assert retained == ["mixed"]
    errored = next(row for row in receipt if row["task"] == "errored")
    assert errored["errors"] == 1
    assert errored["scored_attempts"] == 1


def test_selection_includes_boundary_rates() -> None:
    attempts = [Attempt("boundary", 1 if i < 8 else 0, None) for i in range(10)]
    retained, _ = select(attempts, ["boundary"], minimum=0.1, maximum=0.8)
    assert retained == ["boundary"]


def test_selection_caps_at_eight_with_category_balance() -> None:
    candidates = [f"task-{i}" for i in range(10)]
    attempts = [
        Attempt(task, 1 if attempt % 2 else 0, None) for task in candidates for attempt in range(6)
    ]
    categories = {task: "variant" for task in candidates}
    categories["task-9"] = "rnaseq"
    retained, _ = select(
        attempts,
        candidates,
        minimum=0.1,
        maximum=0.8,
        max_tasks=8,
        category_by_task=categories,
    )
    assert len(retained) == 8
    assert "task-9" in retained


def test_selection_rejects_incomplete_probe_rows() -> None:
    retained, receipt = select(
        [Attempt("partial", 1, None), Attempt("partial", 0, None)],
        ["partial"],
        minimum=0.1,
        maximum=0.8,
        expected_attempts_per_task=6,
    )
    assert retained == []
    assert receipt[0]["attempts_complete"] is False


def test_selection_table_contains_only_retained_tasks(tmp_path: Path) -> None:
    _retained, receipt = select(
        [
            *(Attempt("kept_task", reward, None) for reward in (1, 0, 1, 0, 1, 0)),
            *(Attempt("floor", 0, None) for _ in range(6)),
        ],
        ["kept_task", "floor"],
        minimum=0.1,
        maximum=0.8,
        category_by_task={"kept_task": "variant", "floor": "qc"},
    )
    path = tmp_path / "selection.tex"
    render_selection_table(path, receipt)
    table = path.read_text()
    assert "kept\\_task & variant & 3/6 & 0.50 & 0" in table
    assert "floor" not in table


def test_selector_requires_exactly_twelve_candidates() -> None:
    require_candidate_count([f"task-{index}" for index in range(12)])
    with pytest.raises(RuntimeError, match="exactly 12"):
        require_candidate_count(["only-one"])


def test_selector_requires_two_attempts_from_each_of_three_models() -> None:
    candidates = ["task-a", "task-b"]
    complete_probe = [
        Attempt(task, float(attempt), None)
        for task in candidates
        for attempt in (0, 1)
    ]
    require_probe_shape([complete_probe, complete_probe, complete_probe], candidates)
    with pytest.raises(RuntimeError, match="invalid attempt shape"):
        require_probe_shape([complete_probe, complete_probe, complete_probe[:-1]], candidates)
    with pytest.raises(RuntimeError, match="exactly 3"):
        require_probe_shape([complete_probe, complete_probe], candidates)
