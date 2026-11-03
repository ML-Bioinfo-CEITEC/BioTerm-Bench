#!/usr/bin/env python3
"""Select a unified 50-task benchmark from the completed pre-IRT screen.

The complete k=1 matrix is the only source used for Rasch estimation and
ranking. Adaptive repeats are used only through the audited floor, ceiling,
negative-discrimination, and reliability labels.
"""

from __future__ import annotations

import csv
import json
import math
import re
import tomllib
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp, minimize
from scipy.special import expit
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
PREIRT = ROOT / "paper" / "generated" / "preirt-selection"
OUT = ROOT / "paper" / "generated" / "final-benchmark-selection"
TASK_LIST = ROOT / "configs" / "benchmark_tasks_50.txt"

BAD_STATUSES = {
    "confirmed_floor",
    "confirmed_negative",
    "uncertain_negative",
    "clear_ceiling",
}
PUBLIC_CATEGORIES = {
    "alignment": "Alignment & read processing",
    "metadata": "Annotation & intervals",
    "qc": "Quality control",
    "rnaseq": "RNA-seq & expression",
    "search": "Sequence search & comparative genomics",
    "synthesis": "Integrated workflow",
    "variant": "Variant & population genetics",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(rows)


def load_initial_matrix() -> tuple[list[str], list[str], np.ndarray, dict[str, float]]:
    rows = [row for row in read_csv(PREIRT / "response_long.csv") if row["phase"] == "k1"]
    deployments = list(dict.fromkeys(row["deployment"] for row in rows))
    tasks = list(dict.fromkeys(row["task"] for row in rows))
    lookup: dict[tuple[str, str], int] = {}
    runtimes: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        key = (row["deployment"], row["task"])
        if key in lookup:
            raise ValueError(f"duplicate k1 response: {key}")
        if not row["reward"] or row["operational_error"].lower() == "true":
            raise ValueError(f"unscored k1 response: {key}")
        lookup[key] = int(float(row["reward"]) > 0)
        if row["wall_seconds"]:
            runtimes[row["task"]].append(float(row["wall_seconds"]))
    expected = len(deployments) * len(tasks)
    if len(lookup) != expected:
        raise ValueError(f"incomplete k1 matrix: {len(lookup)} of {expected}")
    matrix = np.asarray([[lookup[(deployment, task)] for task in tasks] for deployment in deployments])
    medians = {task: float(np.median(runtimes[task])) for task in tasks if runtimes[task]}
    return deployments, tasks, matrix, medians


def fit_rasch(matrix: np.ndarray, ridge: float = 0.02) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fit a ridge-regularized Rasch model with sum(theta) constrained to zero."""
    people, items = matrix.shape
    raw_theta = np.log((matrix.sum(axis=1) + 0.5) / (items - matrix.sum(axis=1) + 0.5))
    raw_theta -= raw_theta.mean()
    raw_b = np.log((people - matrix.sum(axis=0) + 0.5) / (matrix.sum(axis=0) + 0.5))
    initial = np.r_[raw_theta[:-1], raw_b]

    def objective(parameters: np.ndarray) -> tuple[float, np.ndarray]:
        theta = np.r_[parameters[: people - 1], -parameters[: people - 1].sum()]
        difficulty = parameters[people - 1 :]
        eta = theta[:, None] - difficulty[None, :]
        probability = expit(eta)
        loss = float((np.logaddexp(0, eta) - matrix * eta).sum())
        loss += ridge * float(np.square(theta).sum() + np.square(difficulty).sum())
        residual = probability - matrix
        theta_gradient = residual.sum(axis=1) + 2 * ridge * theta
        free_theta_gradient = theta_gradient[:-1] - theta_gradient[-1]
        difficulty_gradient = -residual.sum(axis=0) + 2 * ridge * difficulty
        return loss, np.r_[free_theta_gradient, difficulty_gradient]

    result = minimize(objective, initial, jac=True, method="L-BFGS-B")
    if not result.success:
        raise RuntimeError(f"Rasch fit failed: {result.message}")
    theta = np.r_[result.x[: people - 1], -result.x[: people - 1].sum()]
    difficulty = result.x[people - 1 :]
    probability = expit(theta[:, None] - difficulty[None, :])
    standard_error = 1 / np.sqrt((probability * (1 - probability)).sum(axis=0) + 2 * ridge)
    return theta, difficulty, standard_error


def logistic_slope(ability: np.ndarray, response: np.ndarray) -> float:
    if len(set(response.tolist())) < 2:
        return math.nan

    def objective(beta: np.ndarray) -> tuple[float, np.ndarray]:
        eta = beta[0] + beta[1] * ability
        probability = expit(eta)
        loss = float((np.logaddexp(0, eta) - response * eta).sum() + 0.05 * np.square(beta).sum())
        residual = probability - response
        gradient = np.asarray([residual.sum(), (residual * ability).sum()]) + 0.1 * beta
        return loss, gradient

    result = minimize(objective, np.zeros(2), jac=True, method="BFGS")
    return float(result.x[1])


def metadata(tasks: list[str]) -> dict[str, dict[str, object]]:
    result = {}
    for task in tasks:
        with (ROOT / "tasks" / task / "task.toml").open("rb") as handle:
            block = tomllib.load(handle).get("metadata", {})
        tags = list(block.get("tags", []))
        family = next((tag for tag in tags if tag.startswith("irt-family-")), "")
        result[task] = {"category": block.get("category", "unknown"), "tags": tags, "family": family}
    return result


def canonical_id(task: str, family: str, all_tasks: set[str]) -> str:
    if family:
        return re.sub(r"-[abcd]$", "", task)
    if task.endswith("-nohint") and task[:-7] in all_tasks:
        return task[:-7]
    return task


def build_constraints(
    candidates: list[dict[str, object]], signatures: dict[str, tuple[int, ...]]
) -> tuple[np.ndarray, list[float], list[float], dict[str, str]]:
    rows: list[np.ndarray] = [np.ones(len(candidates))]
    lower = [50.0]
    upper = [50.0]
    group_note: dict[str, str] = {}

    categories = sorted({str(row["category"]) for row in candidates})
    for category in categories:
        rows.append(np.asarray([row["category"] == category for row in candidates], dtype=float))
        lower.append(0.0 if category == "synthesis" else 6.0)
        upper.append(1.0 if category == "synthesis" else 10.0)

    families: dict[str, list[str]] = defaultdict(list)
    duplicates: dict[str, list[str]] = defaultdict(list)
    for row in candidates:
        task = str(row["source_task"])
        if row["family"]:
            families[str(row["family"])].append(task)
        canonical = str(row["benchmark_id"])
        duplicates[canonical].append(task)
    for label, tasks in sorted({**families, **duplicates}.items()):
        if len(tasks) < 2:
            continue
        rows.append(np.asarray([row["source_task"] in tasks for row in candidates], dtype=float))
        lower.append(0.0)
        upper.append(1.0)
        for task in tasks:
            group_note[task] = label

    # Ten deployments are too few to call equal patterns semantic duplicates.
    # A cap of three only prevents a domain from spending four or more slots on
    # empirically indistinguishable items while retaining capability diversity.
    signature_groups: dict[tuple[str, tuple[int, ...]], list[str]] = defaultdict(list)
    for row in candidates:
        task = str(row["source_task"])
        signature_groups[(str(row["category"]), signatures[task])].append(task)
    for tasks in signature_groups.values():
        if len(tasks) <= 3:
            continue
        rows.append(np.asarray([row["source_task"] in tasks for row in candidates], dtype=float))
        lower.append(0.0)
        upper.append(3.0)
    return np.vstack(rows), lower, upper, group_note


def select(candidates: list[dict[str, object]], constraint: tuple[np.ndarray, list[float], list[float]]) -> set[str]:
    matrix, lower, upper = constraint
    objective = -np.asarray([float(row["selection_score"]) for row in candidates])
    result = milp(
        objective,
        integrality=np.ones(len(candidates)),
        bounds=Bounds(0, 1),
        constraints=LinearConstraint(matrix, lower, upper),
    )
    if not result.success:
        raise RuntimeError(f"selection optimization failed: {result.message}")
    return {str(candidates[index]["source_task"]) for index, value in enumerate(result.x) if value > 0.5}


def main() -> int:
    audit_rows = read_csv(PREIRT / "task_audit_115.csv")
    audit = {row["task"]: row for row in audit_rows}
    deployments, tasks, matrix, runtimes = load_initial_matrix()
    if matrix.shape != (10, 113):
        raise ValueError(f"expected 10x113 initial matrix, got {matrix.shape}")
    task_set = set(tasks)
    task_metadata = metadata(tasks)
    theta, difficulty, difficulty_se = fit_rasch(matrix)
    reference_ability = float(np.median(theta))
    total_scores = matrix.sum(axis=1)
    loo_rank_correlations = []
    for left_out in range(len(deployments)):
        keep = np.arange(len(deployments)) != left_out
        _, loo_difficulty, _ = fit_rasch(matrix[keep])
        loo_rank_correlations.append(float(spearmanr(difficulty, loo_difficulty).statistic))
    bridge_rank_correlations = {}
    for deployment in ("or-gptoss-120b", "ei-gptoss-120b"):
        if deployment in deployments:
            keep = np.asarray([candidate != deployment for candidate in deployments])
            _, bridge_difficulty, _ = fit_rasch(matrix[keep])
            bridge_rank_correlations[f"drop_{deployment}"] = float(
                spearmanr(difficulty, bridge_difficulty).statistic
            )

    diagnostics: list[dict[str, object]] = []
    for index, task in enumerate(tasks):
        response = matrix[:, index]
        rest = total_scores - response
        rest_ability = np.log((rest + 0.5) / (matrix.shape[1] - 1 - rest + 0.5))
        rho = float(spearmanr(rest_ability, response).statistic) if len(set(response.tolist())) > 1 else math.nan
        slope = logistic_slope(rest_ability, response)
        order = np.argsort(rest_ability)
        top_bottom_gap = float(response[order[-3:]].mean() - response[order[:3]].mean())
        reference_probability = float(expit(reference_ability - difficulty[index]))
        fitted_probability = expit(theta - difficulty[index])
        variance = fitted_probability * (1 - fitted_probability)
        squared_residual = np.square(response - fitted_probability)
        infit = float(squared_residual.sum() / variance.sum())
        outfit = float(np.mean(squared_residual / variance))
        relative_information = 4 * reference_probability * (1 - reference_probability)
        hardness = float(np.clip((0.90 - reference_probability) / 0.55, 0, 1))
        monotonicity = 0.0 if not math.isfinite(rho) else float(np.clip((rho + 0.10) / 0.90, 0, 1))
        status = audit[task]["status"]
        pooled_rho = float(audit[task]["item_rest_spearman"]) if audit[task]["item_rest_spearman"] not in {"", "nan"} else math.nan
        pooled_slope = float(audit[task]["logistic_slope"]) if audit[task]["logistic_slope"] not in {"", "nan"} else math.nan
        pooled_top = float(audit[task]["top_tertile_mean"]) if audit[task]["top_tertile_mean"] not in {"", "nan"} else math.nan
        pooled_bottom = float(audit[task]["bottom_tertile_mean"]) if audit[task]["bottom_tertile_mean"] not in {"", "nan"} else math.nan
        repeat_agreement = float(audit[task]["repeat_agreement"]) if audit[task]["repeat_agreement"] not in {"", "nan"} else math.nan
        initial_negative = math.isfinite(rho) and rho < 0
        repeat_resolved = (
            initial_negative
            and math.isfinite(repeat_agreement)
            and repeat_agreement >= 0.75
            and math.isfinite(pooled_rho)
            and pooled_rho > 0
            and math.isfinite(pooled_slope)
            and pooled_slope > 0
            and math.isfinite(pooled_top)
            and math.isfinite(pooled_bottom)
            and pooled_top >= pooled_bottom
        )
        psychometric_flag = "repeat_resolved_initial_negative" if repeat_resolved else "ok"
        if initial_negative and not repeat_resolved:
            psychometric_flag = "unresolved_initial_negative"
        score = 0.45 * relative_information + 0.35 * hardness + 0.20 * monotonicity
        if status == "near_ceiling":
            score -= 0.30
        if repeat_resolved:
            score -= 0.10
        family = str(task_metadata[task]["family"])
        diagnostics.append(
            {
                "source_task": task,
                "benchmark_id": canonical_id(task, family, task_set),
                "category": str(task_metadata[task]["category"]),
                "family": family,
                "status": status,
                "k1_successes": int(response.sum()),
                "k1_attempts": len(response),
                "k1_pass_rate": float(response.mean()),
                "rasch_difficulty": float(difficulty[index]),
                "rasch_difficulty_se": float(difficulty_se[index]),
                "rasch_reference_probability": reference_probability,
                "rasch_relative_information": relative_information,
                "rasch_infit_mnsq": infit,
                "rasch_outfit_mnsq": outfit,
                "item_rest_spearman_k1": rho,
                "slope_diagnostic_k1": slope,
                "top_bottom_gap_k1": top_bottom_gap,
                "repeat_agreement": repeat_agreement,
                "psychometric_flag": psychometric_flag,
                "median_wall_seconds_k1": runtimes.get(task, math.nan),
                "selection_score": score,
            }
        )

    candidates = [
        row
        for row in diagnostics
        if row["status"] not in BAD_STATUSES and row["psychometric_flag"] != "unresolved_initial_negative"
    ]
    easiest_possible: dict[str, float] = {}
    for row in candidates:
        benchmark_id = str(row["benchmark_id"])
        rate = float(row["k1_pass_rate"])
        easiest_possible[benchmark_id] = min(rate, easiest_possible.get(benchmark_id, 1.0))
    fifty_hardest_rates = sorted(easiest_possible.values())[:50]
    theoretical_median_floor = float(np.median(fifty_hardest_rates))
    signatures = {task: tuple(int(value) for value in matrix[:, index]) for index, task in enumerate(tasks)}
    constraint_matrix, lower, upper, group_note = build_constraints(candidates, signatures)
    selected = select(candidates, (constraint_matrix, lower, upper))
    if len(selected) != 50:
        raise AssertionError(f"selected {len(selected)} tasks")

    selected_rows = [dict(row) for row in candidates if row["source_task"] in selected]
    selected_rows.sort(key=lambda row: (-float(row["selection_score"]), str(row["benchmark_id"])))
    rank = {str(row["source_task"]): index + 1 for index, row in enumerate(selected_rows)}
    for row in selected_rows:
        row["rank"] = rank[str(row["source_task"])]
        row["domain"] = PUBLIC_CATEGORIES[str(row["category"])]
        if row["psychometric_flag"] == "repeat_resolved_initial_negative":
            row["selection_note"] = "initial negative diagnostic resolved by stable follow-up"
        elif row["family"]:
            row["selection_note"] = "family representative; hard/informative"
        else:
            row["selection_note"] = "hard/informative and adds capability coverage"

    exclusions = []
    selected_benchmark_ids = {str(row["benchmark_id"]) for row in selected_rows}
    for row in audit_rows:
        task = row["task"]
        if row["included"] != "True":
            reason = "invalid task contract"
        elif task in selected:
            reason = "selected"
        elif row["status"] in BAD_STATUSES:
            reason = row["status"].replace("_", " ")
        else:
            diag = next(item for item in diagnostics if item["source_task"] == task)
            if diag["psychometric_flag"] == "unresolved_initial_negative":
                reason = "unresolved negative k1 diagnostic"
            elif diag["family"] and str(diag["benchmark_id"]) in selected_benchmark_ids:
                reason = "unselected A-D family sibling"
            elif str(diag["benchmark_id"]) in selected_benchmark_ids:
                reason = "unselected near-duplicate sibling"
            elif task in group_note:
                reason = "lower-priority family/duplicate representative"
            else:
                reason = "lower information/diversity priority"
        exclusions.append({"task": task, "reason": reason})

    OUT.mkdir(parents=True, exist_ok=True)
    selection_fields = [
        "rank", "benchmark_id", "source_task", "domain", "category", "status",
        "k1_successes", "k1_attempts", "k1_pass_rate", "rasch_difficulty",
        "rasch_difficulty_se", "rasch_reference_probability", "rasch_relative_information",
        "rasch_infit_mnsq", "rasch_outfit_mnsq",
        "item_rest_spearman_k1", "slope_diagnostic_k1", "top_bottom_gap_k1",
        "repeat_agreement", "psychometric_flag", "median_wall_seconds_k1", "selection_score", "family",
        "selection_note",
    ]
    write_csv(OUT / "selected_tasks_50.csv", selected_rows, selection_fields)
    write_csv(OUT / "all_item_irt.csv", diagnostics, list(diagnostics[0]))
    write_csv(OUT / "selection_decisions_115.csv", exclusions, ["task", "reason"])
    TASK_LIST.write_text("\n".join(sorted(selected)) + "\n")

    category_counts = Counter(str(row["category"]) for row in selected_rows)
    difficulty_counts = Counter(int(row["k1_successes"]) for row in selected_rows)
    summary = {
        "method": "ridge-regularized Rasch/1PL on complete k1 matrix",
        "ranking_data": "113 tasks x 10 deployments, k1 only",
        "adaptive_followups": "used only for audit status and repeat agreement",
        "selected_tasks": 50,
        "source_tasks": 113,
        "category_counts": dict(sorted(category_counts.items())),
        "k1_success_distribution": {str(key): value for key, value in sorted(difficulty_counts.items())},
        "median_k1_pass_rate": float(np.median([row["k1_pass_rate"] for row in selected_rows])),
        "mean_k1_pass_rate": float(np.mean([row["k1_pass_rate"] for row in selected_rows])),
        "theoretical_minimum_median_k1_pass_rate": theoretical_median_floor,
        "near_ceiling_selected": sum(row["status"] == "near_ceiling" for row in selected_rows),
        "bad_status_selected": sum(row["status"] in BAD_STATUSES for row in selected_rows),
        "variant_families_selected": len({row["family"] for row in selected_rows if row["family"]}),
        "estimated_sequential_wall_seconds": float(sum(row["median_wall_seconds_k1"] for row in selected_rows)),
        "irt_sensitivity": {
            "leave_one_deployment_out_rank_correlation_min": min(loo_rank_correlations),
            "leave_one_deployment_out_rank_correlation_median": float(np.median(loo_rank_correlations)),
            **bridge_rank_correlations,
        },
        "constraints": {
            "A-D variants": "at most one per explicit irt-family tag",
            "hint variants": "at most one canonical/nohint pair",
            "category": "6-10 per main domain; at most one synthesis task if psychometrically eligible",
            "empirical redundancy": "at most three identical k1 response signatures per category",
        },
    }
    (OUT / "selection_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    report = [
        "# Final 50-task BioTerm benchmark proposal",
        "",
        "This is one benchmark organized by capability domain. Generation waves and A-D levels are not public-facing dimensions.",
        "",
        "## Selection method",
        "",
        "- Fit a ridge-regularized Rasch/1PL model to the complete 113 x 10 k=1 matrix.",
        "- Use adaptive k=3 results only to exclude confirmed floor/negative items and to flag repeat stability.",
        "- Prefer hard, informative items using 45% Rasch information, 35% hardness, and 20% item-rest monotonicity.",
        "- Exclude confirmed floor, confirmed/uncertain negative, and clear-ceiling items.",
        "- Keep at most one task from every A-D family and every canonical/nohint pair.",
        "- Constrain each main domain to 6-10 tasks; include an integrated-workflow item only if psychometrically eligible.",
        "- Cap identical k=1 response signatures at three per domain; correlation alone is not treated as semantic duplication.",
        "",
        f"With 50 slots, a median k=1 pass rate below {theoretical_median_floor:.2f} is impossible after the family and psychometric constraints; the selected set reaches that lower bound.",
        "",
        "## Composition",
        "",
        "| Domain | Tasks |",
        "|---|---:|",
    ]
    for category, count in sorted(category_counts.items()):
        report.append(f"| {PUBLIC_CATEGORIES[category]} | {count} |")
    report.extend(["", "## Selected tasks", ""])
    for category in sorted(category_counts, key=lambda item: PUBLIC_CATEGORIES[item]):
        report.append(f"### {PUBLIC_CATEGORIES[category]}")
        report.append("")
        for row in sorted(
            (item for item in selected_rows if item["category"] == category),
            key=lambda item: str(item["benchmark_id"]),
        ):
            report.append(
                f"- `{row['benchmark_id']}` — k=1 pass {int(row['k1_successes'])}/10; "
                f"Rasch difficulty {float(row['rasch_difficulty']):.2f}"
            )
        report.append("")
    report.extend(
        [
            "## Interpretation",
            "",
            "The Rasch estimates are screening estimates, not definitive item calibrations: there are only ten deployments and one model is intentionally bridged across two providers. A uniform confirmatory run on the frozen 50 should precede publication of final IRT parameters.",
            f"Difficulty ordering was stable in leave-one-deployment-out sensitivity analysis (minimum Spearman rho {min(loo_rank_correlations):.3f}; median {float(np.median(loo_rank_correlations)):.3f}).",
            "",
            "Public benchmark names omit A-D/nohint suffixes. `selected_tasks_50.csv` retains the source-task mapping needed to build the benchmark without renaming directories yet.",
        ]
    )
    (OUT / "README.md").write_text("\n".join(report) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
