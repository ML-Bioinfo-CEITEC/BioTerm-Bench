import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v1_freeze_receipt_verifies():
    result = subprocess.run(
        ["python3", "scripts/freeze_benchmark_v1.py", "--verify"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "50 frozen tasks" in result.stdout


def test_v1_manifest_and_task_table_are_consistent():
    manifest = json.loads((ROOT / "configs" / "benchmark_v1.0_manifest.json").read_text())
    with (ROOT / "configs" / "benchmark_v1.0_tasks.tsv").open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert manifest["version"] == "1.0.0"
    assert manifest["status"] == "frozen"
    assert manifest["task_count"] == len(rows) == 50
    assert len({row["public_id"] for row in rows}) == 50
    assert len({row["source_task"] for row in rows}) == 50
    assert manifest["category_counts"] == {
        "alignment": 8,
        "metadata": 8,
        "qc": 6,
        "rnaseq": 8,
        "search": 10,
        "variant": 10,
    }
