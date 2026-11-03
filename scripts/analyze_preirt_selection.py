#!/usr/bin/env python3
"""Build pre-IRT response matrices, diagnostics, and adaptive assignments."""

from __future__ import annotations

import csv
import json
import math
import tomllib
from collections import defaultdict
from datetime import datetime

import numpy as np
from preirt_common import (
    CONFIGS,
    JOBS,
    ROOT,
    assert_frozen_tasks,
    load_panel,
    trial_records,
)
from scipy.optimize import minimize
from scipy.stats import pearsonr, spearmanr

OUT = ROOT / "paper" / "generated" / "preirt-selection"


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def logistic_slope(theta: list[float], successes: list[int], attempts: list[int]) -> float:
    if not theta or sum(successes) in (0, sum(attempts)):
        return math.nan
    x = np.asarray(theta, dtype=float)
    y = np.asarray(successes, dtype=float)
    n = np.asarray(attempts, dtype=float)

    def objective(beta: np.ndarray) -> float:
        eta = np.clip(beta[0] + beta[1] * x, -30, 30)
        probability = 1 / (1 + np.exp(-eta))
        likelihood = -(y * np.log(probability) + (n - y) * np.log(1 - probability)).sum()
        return float(likelihood + 0.05 * (beta**2).sum())

    result = minimize(objective, np.zeros(2), method="BFGS")
    return float(result.x[1])


def mean_or_nan(values: list[float]) -> float:
    return float(np.mean(values)) if values else math.nan


def task_metadata(tasks: list[str]) -> dict[str, dict[str, object]]:
    metadata = {}
    for task in tasks:
        with (ROOT / "tasks" / task / "task.toml").open("rb") as handle:
            config = tomllib.load(handle)
        block = config.get("metadata", {})
        metadata[task] = {
            "category": block.get("category", "unknown"),
            "tags": set(block.get("tags", [])),
        }
    return metadata


def historical_rates(tasks: set[str]) -> dict[str, tuple[int, int]]:
    values: dict[str, list[int]] = defaultdict(list)
    skip = ("preirt-", "pilot-underspecified", ".broken", "provider-outage", "docker-failed")
    for job in JOBS.iterdir():
        if not job.is_dir() or job.name.startswith(".") or any(marker in job.name for marker in skip):
            continue
        for row in trial_records(job):
            if row["task"] in tasks and row["reward"] is not None:
                values[row["task"]].append(int(float(row["reward"]) > 0))
    return {task: (sum(rows), len(rows)) for task, rows in values.items()}


def main() -> int:
    included = assert_frozen_tasks()
    panel = load_panel()
    deployments = [row["deployment"] for row in panel]
    all_tasks = []
    checksum_rows = {}
    with (CONFIGS / "preirt_task_checksums.tsv").open() as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            all_tasks.append(row["task"])
            checksum_rows[row["task"]] = row
    metadata = task_metadata(all_tasks)
    historical = historical_rates(set(all_tasks))
    OUT.mkdir(parents=True, exist_ok=True)

    observations: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    long_rows = []
    job_receipt = {}
    for deployment in deployments:
        for phase in ("k1", "followup"):
            job = JOBS / f"preirt-{phase}-{deployment}"
            rows = trial_records(job) if job.exists() else []
            job_receipt[f"{phase}:{deployment}"] = {
                "path": str(job.relative_to(ROOT)),
                "trials": len(rows),
                "scored": sum(row["reward"] is not None for row in rows),
                "errors": sum(row["reward"] is None for row in rows),
            }
            for row in rows:
                if row["task"] not in included:
                    continue
                observations[(deployment, row["task"])].append(row)
                start, finish = parse_time(row["started_at"]), parse_time(row["finished_at"])
                wall = (finish - start).total_seconds() if start and finish else ""
                long_rows.append(
                    {
                        "deployment": deployment,
                        "phase": phase,
                        "task": row["task"],
                        "reward": "" if row["reward"] is None else row["reward"],
                        "operational_error": row["reward"] is None,
                        "cost_usd": row["cost_usd"],
                        "wall_seconds": wall,
                        "trial": row["trial"],
                        "receipt_path": row["path"],
                    }
                )

    with (OUT / "response_long.csv").open("w", newline="") as handle:
        fields = list(long_rows[0]) if long_rows else [
            "deployment", "phase", "task", "reward", "operational_error",
            "cost_usd", "wall_seconds", "trial", "receipt_path",
        ]
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(long_rows)

    success: dict[tuple[str, str], int] = {}
    attempt: dict[tuple[str, str], int] = {}
    initial_success: dict[tuple[str, str], int] = {}
    for deployment in deployments:
        initial_job = JOBS / f"preirt-k1-{deployment}"
        initial = defaultdict(list)
        if initial_job.exists():
            for row in trial_records(initial_job):
                if row["task"] in included and row["reward"] is not None:
                    initial[row["task"]].append(int(float(row["reward"]) > 0))
        for task in included:
            scored = [
                int(float(row["reward"]) > 0)
                for row in observations.get((deployment, task), [])
                if row["reward"] is not None
            ]
            success[(deployment, task)] = sum(scored)
            attempt[(deployment, task)] = len(scored)
            initial_success[(deployment, task)] = sum(initial.get(task, []))

    with (OUT / "response_matrix.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["deployment", *included])
        for deployment in deployments:
            writer.writerow(
                [deployment]
                + [
                    "" if not attempt[(deployment, task)] else success[(deployment, task)] / attempt[(deployment, task)]
                    for task in included
                ]
            )

    ability = {}
    for deployment in deployments:
        wins = sum(initial_success[(deployment, task)] for task in included)
        trials = sum(min(1, attempt[(deployment, task)]) for task in included)
        ability[deployment] = math.log((wins + 0.5) / (trials - wins + 0.5)) if trials else math.nan
    ordered_ability = sorted(
        (deployment for deployment in deployments if math.isfinite(ability[deployment])),
        key=lambda deployment: ability[deployment],
    )
    weakest = ordered_ability[:3]
    strongest = ordered_ability[-3:]

    diagnostics = {}
    assignments: dict[tuple[str, str], set[str]] = defaultdict(set)
    for task in included:
        complete = [d for d in deployments if attempt[(d, task)] >= 1]
        theta = []
        values = []
        counts = []
        totals = []
        for deployment in complete:
            other_wins = sum(initial_success[(deployment, other)] for other in included if other != task)
            other_n = sum(min(1, attempt[(deployment, other)]) for other in included if other != task)
            theta.append(math.log((other_wins + 0.5) / (other_n - other_wins + 0.5)))
            counts.append(success[(deployment, task)])
            totals.append(attempt[(deployment, task)])
            values.append(success[(deployment, task)] / attempt[(deployment, task)])
        rho = float(spearmanr(theta, values).statistic) if len(set(values)) > 1 and len(theta) >= 3 else math.nan
        slope = logistic_slope(theta, counts, totals)
        initial_passes = sum(initial_success[(d, task)] > 0 for d in deployments)
        trigger = []
        if len(complete) == 10:
            if initial_passes == 0:
                trigger.append("zero")
                for deployment in strongest:
                    assignments[(deployment, task)].add("zero")
            if 1 <= initial_passes <= 3:
                trigger.append("sparse")
                for deployment in deployments:
                    assignments[(deployment, task)].add("sparse")
            if initial_passes >= 9:
                trigger.append("ceiling")
                for deployment in weakest:
                    assignments[(deployment, task)].add("ceiling")
            if (math.isfinite(rho) and rho < 0) or (math.isfinite(slope) and slope < 0):
                trigger.append("negative")
                for deployment in deployments:
                    assignments[(deployment, task)].add("negative")

        repeated = [d for d in deployments if attempt[(d, task)] >= 3]
        agreement = []
        for deployment in repeated:
            p = success[(deployment, task)] / attempt[(deployment, task)]
            agreement.append(max(p, 1 - p))
        repeat_agreement = float(np.mean(agreement)) if agreement else math.nan
        top_mean = mean_or_nan(
            [success[(d, task)] / attempt[(d, task)] for d in strongest if attempt[(d, task)]]
        )
        bottom_mean = mean_or_nan(
            [success[(d, task)] / attempt[(d, task)] for d in weakest if attempt[(d, task)]]
        )
        total_success = sum(success[(d, task)] for d in deployments)
        total_attempt = sum(attempt[(d, task)] for d in deployments)
        hist_s, hist_n = historical.get(task, (0, 0))

        status = "incomplete"
        if len(complete) == 10:
            status = "informative"
            if initial_passes == 0:
                status = "floor_followup_needed"
                if strongest and all(attempt[(d, task)] >= 3 for d in strongest):
                    status = "confirmed_floor" if total_success == 0 else "fragile_hard"
            elif initial_passes >= 9:
                status = "ceiling_followup_needed"
                if weakest and all(attempt[(d, task)] >= 3 for d in weakest):
                    weak_perfect = all(success[(d, task)] == attempt[(d, task)] for d in weakest)
                    status = "clear_ceiling" if weak_perfect and hist_n and hist_s / hist_n >= 0.95 else "near_ceiling"
            if repeated and math.isfinite(rho) and math.isfinite(slope):
                if rho < 0 and slope < 0 and top_mean < bottom_mean:
                    status = "confirmed_negative"
                elif rho < 0 or slope < 0:
                    status = "uncertain_negative"

        diagnostics[task] = {
            "initial_model_successes": initial_passes,
            "successes": total_success,
            "attempts": total_attempt,
            "model_coverage": len(complete),
            "logistic_slope": slope,
            "item_rest_spearman": rho,
            "repeat_agreement": repeat_agreement,
            "top_tertile_mean": top_mean,
            "bottom_tertile_mean": bottom_mean,
            "historical_successes": hist_s,
            "historical_attempts": hist_n,
            "followup_trigger": ",".join(trigger),
            "status": status,
        }

    with (CONFIGS / "preirt_followup_assignments.tsv").open("w") as handle:
        handle.write("deployment\ttask\treasons\tadditional_attempts\n")
        for (deployment, task), reasons in sorted(assignments.items()):
            handle.write(f"{deployment}\t{task}\t{','.join(sorted(reasons))}\t2\n")

    audit_fields = [
        "task", "validity", "included", "category", "successes", "attempts",
        "model_coverage", "initial_model_successes", "logistic_slope",
        "item_rest_spearman", "repeat_agreement", "top_tertile_mean",
        "bottom_tertile_mean", "historical_successes", "historical_attempts",
        "followup_trigger", "status", "notes",
    ]
    audit_rows = []
    for task in sorted(all_tasks):
        included_flag = checksum_rows[task]["included"] == "True"
        diag = diagnostics.get(task, {})
        audit_rows.append(
            {
                "task": task,
                "validity": "valid" if included_flag else "invalid_contract",
                "included": included_flag,
                "category": metadata[task]["category"],
                **{field: diag.get(field, "") for field in audit_fields if field not in {"task", "validity", "included", "category", "notes"}},
                "notes": checksum_rows[task]["note"],
            }
        )
    with (OUT / "task_audit_115.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, audit_fields)
        writer.writeheader()
        writer.writerows(audit_rows)

    diag_fields = ["task", *next(iter(diagnostics.values())).keys()] if diagnostics else ["task"]
    with (OUT / "item_diagnostics.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, diag_fields)
        writer.writeheader()
        writer.writerows({"task": task, **row} for task, row in sorted(diagnostics.items()))

    # Empirical redundancy requires complete deployment coverage and semantic overlap.
    parent = {task: task for task in included}

    def find(task: str) -> str:
        while parent[task] != task:
            parent[task] = parent[parent[task]]
            task = parent[task]
        return task

    def union(a: str, b: str) -> None:
        a, b = find(a), find(b)
        if a != b:
            parent[b] = a

    redundancy_edges = []
    for index, left in enumerate(included):
        left_values = [success[(d, left)] / attempt[(d, left)] if attempt[(d, left)] else math.nan for d in deployments]
        for right in included[index + 1 :]:
            if metadata[left]["category"] != metadata[right]["category"]:
                continue
            if not (metadata[left]["tags"] & metadata[right]["tags"]):
                continue
            right_values = [success[(d, right)] / attempt[(d, right)] if attempt[(d, right)] else math.nan for d in deployments]
            pairs = [(a, b) for a, b in zip(left_values, right_values) if math.isfinite(a) and math.isfinite(b)]
            if len(pairs) < 6 or len({a for a, _ in pairs}) < 2 or len({b for _, b in pairs}) < 2:
                continue
            correlation = float(pearsonr([a for a, _ in pairs], [b for _, b in pairs]).statistic)
            if correlation >= 0.90:
                union(left, right)
                redundancy_edges.append((left, right, correlation))
    with (OUT / "redundancy_edges.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["task_a", "task_b", "response_correlation"])
        writer.writerows(redundancy_edges)
    clusters = defaultdict(list)
    for task in included:
        clusters[find(task)].append(task)
    with (OUT / "redundancy_clusters.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["cluster", "size", "tasks"])
        for number, tasks in enumerate((v for v in clusters.values() if len(v) > 1), start=1):
            writer.writerow([number, len(tasks), ";".join(sorted(tasks))])

    category_counts = defaultdict(lambda: [0, 0])
    for row in audit_rows:
        category_counts[row["category"]][0] += 1
        category_counts[row["category"]][1] += int(bool(row["included"]))
    with (OUT / "category_counts.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["category", "audit_tasks", "included_tasks"])
        for category, counts in sorted(category_counts.items()):
            writer.writerow([category, *counts])

    bridge_rows = []
    for task in included:
        left, right = "or-gptoss-120b", "ei-gptoss-120b"
        if attempt[(left, task)] and attempt[(right, task)]:
            a = success[(left, task)] / attempt[(left, task)]
            b = success[(right, task)] / attempt[(right, task)]
            bridge_rows.append((task, a, b, a - b))
    with (OUT / "provider_bridge_gptoss.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["task", "openrouter_mean", "einfra_mean", "difference"])
        writer.writerows(bridge_rows)

    receipt = {
        "audit_rows": len(audit_rows),
        "included_tasks": len(included),
        "deployments": deployments,
        "initial_complete_cells": sum(attempt[(d, t)] >= 1 for d in deployments for t in included),
        "required_initial_cells": len(deployments) * len(included),
        "followup_assignments": len(assignments),
        "jobs": job_receipt,
        "primary_data_policy": "preirt jobs only; historical receipts are sensitivity fields",
    }
    (OUT / "verification_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
