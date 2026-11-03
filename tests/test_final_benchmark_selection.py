import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "generated" / "final-benchmark-selection"


def selected_rows():
    with (OUT / "selected_tasks_50.csv").open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_final_selection_has_fifty_unique_valid_tasks():
    rows = selected_rows()
    assert len(rows) == 50
    assert len({row["source_task"] for row in rows}) == 50
    assert len({row["benchmark_id"] for row in rows}) == 50
    assert all((ROOT / "tasks" / row["source_task"]).is_dir() for row in rows)
    assert not {row["status"] for row in rows} & {
        "confirmed_floor",
        "confirmed_negative",
        "uncertain_negative",
        "clear_ceiling",
    }


def test_final_selection_uses_one_task_per_abcd_family():
    rows = selected_rows()
    canonical = [re.sub(r"-[abcd]$", "", row["source_task"]) for row in rows]
    assert len(canonical) == len(set(canonical))
    families = [row["family"] for row in rows if row["family"]]
    assert len(families) == len(set(families))


def test_final_selection_is_balanced_and_hard():
    rows = selected_rows()
    counts = {}
    for row in rows:
        counts[row["category"]] = counts.get(row["category"], 0) + 1
    assert counts.get("synthesis", 0) <= 1
    assert all(6 <= count <= 10 for category, count in counts.items() if category != "synthesis")
    rates = sorted(float(row["k1_pass_rate"]) for row in rows)
    assert (rates[24] + rates[25]) / 2 <= 0.75


def test_final_selection_receipt_and_manifest_agree():
    rows = selected_rows()
    summary = json.loads((OUT / "selection_summary.json").read_text())
    manifest = [line for line in (ROOT / "configs" / "benchmark_tasks_50.txt").read_text().splitlines() if line]
    assert summary["selected_tasks"] == 50
    assert summary["bad_status_selected"] == 0
    assert set(manifest) == {row["source_task"] for row in rows}
