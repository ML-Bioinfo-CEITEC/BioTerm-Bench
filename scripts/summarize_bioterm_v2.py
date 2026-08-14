#!/usr/bin/env python3
"""Summarize BioTerm-Bench repeated-run results for paper-ready reporting."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import tomllib
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

LABEL_OVERRIDES = {
    "openrouter/google/gemma-4-26b-a4b-it": "Gemma 4 26B A4B",
    "openrouter/google/gemma-4-31b-it": "Gemma 4 31B",
    "openrouter/openai/gpt-oss-20b": "GPT-OSS 20B",
    "openrouter/mistralai/mistral-small-3.1-24b-instruct": "Mistral Small 3.1 24B",
    "openrouter/mistralai/mistral-small-3.2-24b-instruct": "Mistral Small 3.2 24B",
    "openrouter/mistralai/mistral-small-24b-instruct-2501": "Mistral Small 2501",
    "openrouter/mistralai/mistral-nemo": "Mistral Nemo",
    "openrouter/mistralai/ministral-8b-2512": "Ministral 8B",
    "openrouter/mistralai/ministral-14b-2512": "Ministral 14B",
    "openrouter/qwen/qwen3-8b": "Qwen 3 8B",
    "openrouter/qwen/qwen3-14b": "Qwen 3 14B",
    "openrouter/qwen/qwen3-30b-a3b": "Qwen 3 30B A3B",
    "openrouter/qwen/qwen3.5-9b": "Qwen 3.5 9B",
    "openrouter/qwen/qwen-2.5-7b-instruct": "Qwen 2.5 7B",
    "openrouter/qwen/qwen3.6-flash": "Qwen 3.6 Flash",
    "openrouter/z-ai/glm-4.5-air": "GLM 4.5 Air",
    "openrouter/nvidia/nemotron-3.5-lightning": "Nemotron 3.5 Lightning",
    "openrouter/thinkingmachines/inkling-small": "Inkling Small",
    "openrouter/meta/muse-glimmer-30b": "Muse Glimmer 30B",
    "openrouter/qwen/qwen3.6-35b-a3b": "Qwen 3.6 35B A3B",
    "openrouter/openai/gpt-5.6-luna": "GPT-5.6 Luna",
}


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def latex_escape(value: str) -> str:
    return (
        value.replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("$", "\\$")
        .replace("#", "\\#")
        .replace("_", "\\_")
    )


def stable_seed(*parts: str) -> int:
    digest = hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def cumulative_binomial(n: int, k_max: int, p: float) -> float:
    return sum(math.comb(n, k) * (p**k) * ((1 - p) ** (n - k)) for k in range(k_max + 1))


def clopper_pearson_interval(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    if k == 0:
        lower = 0.0
    else:
        lo, hi = 0.0, k / n
        target = alpha / 2
        for _ in range(80):
            mid = (lo + hi) / 2
            tail = 1.0 - cumulative_binomial(n, k - 1, mid)
            if tail > target:
                hi = mid
            else:
                lo = mid
        lower = (lo + hi) / 2
    if k == n:
        upper = 1.0
    else:
        lo, hi = k / n, 1.0
        target = alpha / 2
        for _ in range(80):
            mid = (lo + hi) / 2
            cdf = cumulative_binomial(n, k, mid)
            if cdf > target:
                lo = mid
            else:
                hi = mid
        upper = (lo + hi) / 2
    return lower, upper


def bootstrap_mean_interval(values: list[float], seed: int, iters: int = 5000) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return values[0], values[0]
    rng = random.Random(seed)
    means = []
    for _ in range(iters):
        means.append(statistics.fmean(rng.choice(values) for _ in range(len(values))))
    means.sort()
    return means[int(0.025 * iters)], means[min(iters - 1, int(0.975 * iters))]


def bootstrap_clustered_reward_interval(
    task_rewards: list[list[float]], seed: int, iters: int = 5000
) -> tuple[float, float]:
    """Bootstrap tasks while retaining every scored attempt within a sampled task."""
    task_rewards = [values for values in task_rewards if values]
    if not task_rewards:
        return 0.0, 0.0
    if len(task_rewards) == 1:
        value = statistics.fmean(task_rewards[0])
        return value, value
    rng = random.Random(seed)
    means = []
    for _ in range(iters):
        sampled = [rng.choice(task_rewards) for _ in range(len(task_rewards))]
        flat = [reward for values in sampled for reward in values]
        means.append(statistics.fmean(flat))
    means.sort()
    return means[int(0.025 * iters)], means[min(iters - 1, int(0.975 * iters))]


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(ys)
    dx = [x - mean_x for x in xs]
    dy = [y - mean_y for y in ys]
    sxx = sum(x * x for x in dx)
    syy = sum(y * y for y in dy)
    if sxx <= 0 or syy <= 0:
        return None
    return sum(x * y for x, y in zip(dx, dy)) / math.sqrt(sxx * syy)


def model_label(model_id: str) -> str:
    if model_id in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[model_id]
    return model_id.split("/")[-1].replace("-", " ").title()


def infer_job_provider(job_name: str, model_id: str) -> str:
    if job_name.startswith("einfra-"):
        return "einfra"
    if model_id.startswith("openrouter/"):
        return "openrouter"
    return "unknown"


@dataclass
class TaskMeta:
    name: str
    category: str
    difficulty: str
    tags: list[str]


@dataclass
class TrialRecord:
    job_name: str
    task: str
    trial_name: str
    model_id: str
    started_at: str
    reward: float | None
    verifier_present: bool
    exception_type: str | None
    exception_message: str | None
    cost_usd: float
    input_tokens: int
    output_tokens: int
    cache_tokens: int
    episodes: int
    rollout_count: int

    @property
    def is_error(self) -> bool:
        return self.exception_type is not None or not self.verifier_present or self.reward is None

    @property
    def is_scored(self) -> bool:
        return not self.is_error


@dataclass
class TaskOutcome:
    task: str
    scored_rewards: list[float]
    n_error_attempts: int
    n_scored_attempts: int
    first_attempt_scored: bool
    first_attempt_reward: float | None
    category: str
    difficulty: str


@dataclass
class ModelSummary:
    cohort: str
    job_name: str
    model_id: str
    model_label: str
    status: str
    status_reason: str
    n_tasks: int
    n_trials: int
    expected_trials: int
    verifier_coverage: float
    zero_token_missing_rate: float
    error_rate: float
    mean_reward: float
    mean_reward_ci_low: float
    mean_reward_ci_high: float
    pass_at_1_count: int
    pass_at_1_scored_denominator: int
    pass_at_1: float
    pass_at_1_ci_low: float
    pass_at_1_ci_high: float
    pass_at_k_count: int
    pass_at_k_scored_denominator: int
    pass_at_k: float
    pass_at_k_ci_low: float
    pass_at_k_ci_high: float
    all_scored_pass_count: int
    all_scored_pass_rate: float
    mixed_count: int
    mixed_rate: float
    failed_task_count: int
    scored_task_count: int
    error_trial_count: int
    total_cost_usd: float
    wall_min: float | None


def load_task_metadata(tasks_dir: Path) -> dict[str, TaskMeta]:
    metadata: dict[str, TaskMeta] = {}
    for task_toml in sorted(tasks_dir.glob("*/task.toml")):
        payload = tomllib.loads(task_toml.read_text())
        meta = payload.get("metadata") or {}
        metadata[task_toml.parent.name] = TaskMeta(
            name=task_toml.parent.name,
            category=meta.get("category") or "unknown",
            difficulty=meta.get("difficulty") or "unknown",
            tags=list(meta.get("tags") or []),
        )
    return metadata


def reward_value(payload: dict[str, Any]) -> float | None:
    rewards = (payload.get("verifier_result") or {}).get("rewards") or {}
    value = rewards.get("reward")
    return None if value is None else float(value)


def read_trials(job_dir: Path) -> list[TrialRecord]:
    trials: list[TrialRecord] = []
    for trial_dir in sorted(job_dir.iterdir()):
        result_path = trial_dir / "result.json"
        if not trial_dir.is_dir() or not result_path.exists():
            continue
        payload = json.loads(result_path.read_text())
        agent = ((payload.get("config") or {}).get("agent") or {})
        agent_result = payload.get("agent_result") or {}
        metadata = agent_result.get("metadata") or {}
        exc = payload.get("exception_info") or {}
        trials.append(
            TrialRecord(
                job_name=job_dir.name,
                task=payload.get("task_name") or "",
                trial_name=payload.get("trial_name") or trial_dir.name,
                model_id=agent.get("model_name") or "",
                started_at=payload.get("started_at") or "",
                reward=reward_value(payload),
                verifier_present=payload.get("verifier_result") is not None,
                exception_type=exc.get("exception_type"),
                exception_message=exc.get("exception_message"),
                cost_usd=float(agent_result.get("cost_usd") or 0.0),
                input_tokens=int(agent_result.get("n_input_tokens") or 0),
                output_tokens=int(agent_result.get("n_output_tokens") or 0),
                cache_tokens=int(agent_result.get("n_cache_tokens") or 0),
                episodes=int(metadata.get("n_episodes") or 0),
                rollout_count=len(agent_result.get("rollout_details") or []),
            )
        )
    return trials


def classify_status(
    result: dict[str, Any],
    trials: list[TrialRecord],
    expected_trials: int,
    attempts_per_task: int,
    max_error_rate: float,
    retired_trials: int = 0,
) -> tuple[str, str]:
    """Classify a job.

    ``expected_trials`` is the budget for the *scored* task set. A job that ran
    a since-retired task legitimately recorded more trials than that, so the
    integrity check adds ``retired_trials`` back before comparing; otherwise
    retiring a task would exclude every job that predates the decision.
    """
    if result.get("finished_at") is None:
        return "excluded", "unfinished"
    if result.get("n_total_trials") != expected_trials + retired_trials:
        return "excluded", "unexpected_trial_budget"
    if len(trials) != expected_trials:
        return "excluded", "missing_trial_records"
    unique_tasks = {trial.task for trial in trials}
    if not unique_tasks or len(trials) % max(1, len(unique_tasks)) != 0:
        return "excluded", "task_trial_shape_mismatch"
    observed_attempts = len(trials) // len(unique_tasks)
    if observed_attempts != attempts_per_task:
        return "excluded", "attempt_count_mismatch"
    error_rate = safe_div(sum(1 for trial in trials if trial.is_error), expected_trials)
    if error_rate > max_error_rate:
        return "excluded", "protocol_failure_high_error_rate"
    return "included", "eligible"


def summarize_job(
    cohort_name: str,
    job_dir: Path,
    task_metadata: dict[str, TaskMeta],
    expected_trials: int,
    attempts_per_task: int,
    max_error_rate: float,
    excluded_tasks: frozenset[str] = frozenset(),
) -> tuple[ModelSummary, dict[str, TaskOutcome]]:
    result = json.loads((job_dir / "result.json").read_text())
    trials = read_trials(job_dir)
    # A retired task's trials stay on disk and in the raw receipts; they are
    # dropped here so the scored aggregate reflects the current task set. The
    # expected-trial count shrinks with it, or every job would look unfinished.
    retired_trials = 0
    if excluded_tasks:
        dropped_tasks = {t.task for t in trials} & excluded_tasks
        trials = [t for t in trials if t.task not in excluded_tasks]
        retired_trials = len(dropped_tasks) * attempts_per_task
        expected_trials -= retired_trials
    status, status_reason = classify_status(
        result, trials, expected_trials, attempts_per_task, max_error_rate, retired_trials
    )

    verifier_coverage = safe_div(sum(1 for trial in trials if trial.verifier_present), expected_trials)
    zero_token_missing_rate = safe_div(
        sum(1 for trial in trials if not trial.verifier_present and trial.input_tokens == 0 and trial.output_tokens == 0),
        expected_trials,
    )
    error_trial_count = sum(1 for trial in trials if trial.is_error)
    error_rate = safe_div(error_trial_count, expected_trials)

    by_task: dict[str, list[TrialRecord]] = defaultdict(list)
    for trial in trials:
        by_task[trial.task].append(trial)

    task_outcomes: dict[str, TaskOutcome] = {}
    for task_name, task_trials in by_task.items():
        task_trials.sort(key=lambda item: item.started_at)
        first = task_trials[0] if task_trials else None
        meta = task_metadata.get(task_name) or TaskMeta(task_name, "unknown", "unknown", [])
        scored_rewards = [trial.reward for trial in task_trials if trial.is_scored and trial.reward is not None]
        task_outcomes[task_name] = TaskOutcome(
            task=task_name,
            scored_rewards=scored_rewards,
            n_error_attempts=sum(1 for trial in task_trials if trial.is_error),
            n_scored_attempts=len(scored_rewards),
            first_attempt_scored=bool(first and first.is_scored),
            first_attempt_reward=first.reward if first and first.is_scored else None,
            category=meta.category,
            difficulty=meta.difficulty,
        )

    scored_trial_rewards = [trial.reward for trial in trials if trial.is_scored and trial.reward is not None]
    scored_task_rewards = [
        outcome.scored_rewards for outcome in task_outcomes.values() if outcome.scored_rewards
    ]

    pass_at_1_scored_denominator = sum(1 for outcome in task_outcomes.values() if outcome.first_attempt_scored)
    pass_at_1_count = sum(
        1
        for outcome in task_outcomes.values()
        if outcome.first_attempt_scored and (outcome.first_attempt_reward or 0.0) >= 1.0
    )
    pass_at_k_scored_denominator = sum(1 for outcome in task_outcomes.values() if outcome.scored_rewards)
    pass_at_k_count = sum(
        1 for outcome in task_outcomes.values() if outcome.scored_rewards and any(reward >= 1.0 for reward in outcome.scored_rewards)
    )
    all_scored_pass_count = sum(
        1 for outcome in task_outcomes.values() if outcome.scored_rewards and all(reward >= 1.0 for reward in outcome.scored_rewards)
    )
    mixed_count = sum(
        1
        for outcome in task_outcomes.values()
        if outcome.scored_rewards and any(reward >= 1.0 for reward in outcome.scored_rewards) and any(reward < 1.0 for reward in outcome.scored_rewards)
    )
    failed_task_count = sum(
        1 for outcome in task_outcomes.values() if outcome.scored_rewards and all(reward < 1.0 for reward in outcome.scored_rewards)
    )
    scored_task_count = pass_at_k_scored_denominator

    pass1_lo, pass1_hi = clopper_pearson_interval(pass_at_1_count, pass_at_1_scored_denominator)
    passk_lo, passk_hi = clopper_pearson_interval(pass_at_k_count, pass_at_k_scored_denominator)
    mean_lo, mean_hi = bootstrap_clustered_reward_interval(
        scored_task_rewards, stable_seed(cohort_name, job_dir.name, "mean")
    )

    model_id = trials[0].model_id if trials else ""
    top_started = parse_ts(result.get("started_at"))
    top_finished = parse_ts(result.get("finished_at"))
    wall_min = None
    if top_started and top_finished:
        wall_min = (top_finished - top_started).total_seconds() / 60

    summary = ModelSummary(
        cohort=cohort_name,
        job_name=job_dir.name,
        model_id=model_id,
        model_label=model_label(model_id),
        status=status,
        status_reason=status_reason,
        n_tasks=len(task_outcomes),
        n_trials=len(trials),
        expected_trials=expected_trials,
        verifier_coverage=verifier_coverage,
        zero_token_missing_rate=zero_token_missing_rate,
        error_rate=error_rate,
        mean_reward=statistics.fmean(scored_trial_rewards) if scored_trial_rewards else 0.0,
        mean_reward_ci_low=mean_lo,
        mean_reward_ci_high=mean_hi,
        pass_at_1_count=pass_at_1_count,
        pass_at_1_scored_denominator=pass_at_1_scored_denominator,
        pass_at_1=safe_div(pass_at_1_count, pass_at_1_scored_denominator),
        pass_at_1_ci_low=pass1_lo,
        pass_at_1_ci_high=pass1_hi,
        pass_at_k_count=pass_at_k_count,
        pass_at_k_scored_denominator=pass_at_k_scored_denominator,
        pass_at_k=safe_div(pass_at_k_count, pass_at_k_scored_denominator),
        pass_at_k_ci_low=passk_lo,
        pass_at_k_ci_high=passk_hi,
        all_scored_pass_count=all_scored_pass_count,
        all_scored_pass_rate=safe_div(all_scored_pass_count, scored_task_count),
        mixed_count=mixed_count,
        mixed_rate=safe_div(mixed_count, scored_task_count),
        failed_task_count=failed_task_count,
        scored_task_count=scored_task_count,
        error_trial_count=error_trial_count,
        total_cost_usd=sum(trial.cost_usd for trial in trials),
        wall_min=wall_min,
    )
    return summary, task_outcomes


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


#: Providers that bill per token, where a summed ``cost_usd`` is a real price.
#: litellm still emits a cost for models it cannot price -- it logs "isn't
#: mapped yet" and falls back -- so on a university-hosted endpoint the figure
#: is an artifact of a price map that does not apply to that service. Printing
#: it as dollars would be a fabricated number, so the column is dropped.
BILLED_PROVIDERS = frozenset({"openrouter", "openai"})

#: Suffixes appended when a job is set aside after an infrastructure failure.
ARCHIVED_JOB_MARKERS = (
    ".docker-failed-",
    ".provider-outage-",
    ".errored-",
    ".partial-",
)


def render_headline_table(
    path: Path,
    rows: list[ModelSummary],
    attempts_per_task: int,
    provider: str = "unknown",
) -> None:
    # Mean reward leads: a practitioner runs a task once, so the fraction of
    # individual attempts that succeed is the operative number. pass@k is kept
    # last because it describes a supervised best-of-n workflow.
    show_cost = provider in BILLED_PROVIDERS
    column_spec = "lrrrrrr" if show_cost else "lrrrrr"
    header = f"Model & mean reward & pass@1 & all-scored & mixed & pass@{attempts_per_task}"
    if show_cost:
        header += " & Cost (USD)"
    lines = [
        f"\\begin{{tabular}}{{{column_spec}}}",
        "\\toprule",
        f"{header} \\\\",
        "\\midrule",
    ]
    for row in rows:
        line = (
            f"{latex_escape(row.model_label)} & {row.mean_reward:.3f} "
            f"& {row.pass_at_1_count}/{row.pass_at_1_scored_denominator} "
            f"& {row.all_scored_pass_count}/{row.scored_task_count} "
            f"& {row.mixed_count}/{row.scored_task_count} "
            f"& {row.pass_at_k_count}/{row.pass_at_k_scored_denominator}"
        )
        if show_cost:
            line += f" & {row.total_cost_usd:.2f}"
        lines.append(line + " \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}"])
    path.write_text("\n".join(lines) + "\n")


def render_exclusion_table(path: Path, rows: list[ModelSummary]) -> None:
    lines = [
        "\\begin{tabular}{llrrr}",
        "\\toprule",
        "Model & Reason & Error rate & Error trials & Verifier cov. \\\\",
        "\\midrule",
    ]
    for row in rows:
        lines.append(
            f"{latex_escape(row.model_label)} & {latex_escape(row.status_reason.replace('_', ' '))} "
            f"& {row.error_rate:.2f} & {row.error_trial_count} & {row.verifier_coverage:.2f} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}"])
    path.write_text("\n".join(lines) + "\n")


def render_task_table(path: Path, rows: list[dict[str, Any]], attempts_per_task: int) -> None:
    lines = [
        "\\begin{tabular}{llrrr}",
        "\\toprule",
        f"Task & Category & pass@{attempts_per_task} models & Mean reward & Disc. \\\\",
        "\\midrule",
    ]
    for row in rows:
        disc = "--" if row["discrimination"] == "" else f"{row['discrimination']:.2f}"
        lines.append(
            f"{latex_escape(row['task'])} & {latex_escape(row['category'])} "
            f"& {row['models_pass_at_k']}/{row['n_models_scored']} "
            f"& {row['mean_reward']:.3f} & {disc} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}"])
    path.write_text("\n".join(lines) + "\n")


def analyze(
    jobs_dir: Path,
    tasks_dir: Path,
    pattern: str,
    cohort_name: str,
    expected_trials: int,
    attempts_per_task: int,
    max_error_rate: float,
    out_dir: Path,
    provider: str = "unknown",
    score_scope: str = "unspecified",
    excluded_tasks: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    task_metadata = load_task_metadata(tasks_dir)
    summaries: list[ModelSummary] = []
    outcomes_by_job: dict[str, dict[str, TaskOutcome]] = {}

    for job_dir in sorted(jobs_dir.glob(pattern)):
        if not job_dir.is_dir() or not (job_dir / "result.json").exists():
            continue
        # Archived receipts are preserved evidence of an infrastructure failure,
        # not members of the cohort. Counting them puts the same model in a
        # table twice -- once for the outage and once for the clean re-run.
        if any(marker in job_dir.name for marker in ARCHIVED_JOB_MARKERS):
            continue
        summary, outcomes = summarize_job(
            cohort_name=cohort_name,
            job_dir=job_dir,
            task_metadata=task_metadata,
            expected_trials=expected_trials,
            excluded_tasks=excluded_tasks,
            attempts_per_task=attempts_per_task,
            max_error_rate=max_error_rate,
        )
        summaries.append(summary)
        outcomes_by_job[job_dir.name] = outcomes

    observed_providers = {
        infer_job_provider(summary.job_name, summary.model_id) for summary in summaries
    }
    observed_providers.discard("unknown")
    if len(observed_providers) > 1:
        raise RuntimeError(
            f"Pattern {pattern!r} mixes provider cohorts: {sorted(observed_providers)}"
        )
    if provider != "unknown" and observed_providers and observed_providers != {provider}:
        raise RuntimeError(
            f"Declared provider {provider!r} does not match jobs: {sorted(observed_providers)}"
        )

    included = sorted(
        [row for row in summaries if row.status == "included"],
        key=lambda item: (-item.pass_at_k, -item.pass_at_1, item.model_label),
    )
    excluded = sorted(
        [row for row in summaries if row.status != "included"],
        key=lambda item: (item.status_reason, item.model_label),
    )

    model_rows = [
        {
            "cohort": row.cohort,
            "provider": provider,
            "run_date": str(
                json.loads((jobs_dir / row.job_name / "result.json").read_text()).get(
                    "started_at", ""
                )
            )[:10],
            "score_scope": score_scope,
            "job_name": row.job_name,
            "model_id": row.model_id,
            "model_label": row.model_label,
            "status": row.status,
            "status_reason": row.status_reason,
            "n_tasks": row.n_tasks,
            "n_trials": row.n_trials,
            "expected_trials": row.expected_trials,
            "verifier_coverage": row.verifier_coverage,
            "zero_token_missing_rate": row.zero_token_missing_rate,
            "error_rate": row.error_rate,
            "mean_reward": row.mean_reward,
            "mean_reward_ci_low": row.mean_reward_ci_low,
            "mean_reward_ci_high": row.mean_reward_ci_high,
            "pass_at_1_count": row.pass_at_1_count,
            "pass_at_1_scored_denominator": row.pass_at_1_scored_denominator,
            "pass_at_1": row.pass_at_1,
            "pass_at_1_ci_low": row.pass_at_1_ci_low,
            "pass_at_1_ci_high": row.pass_at_1_ci_high,
            "pass_at_k_count": row.pass_at_k_count,
            "pass_at_k_scored_denominator": row.pass_at_k_scored_denominator,
            "pass_at_k": row.pass_at_k,
            "pass_at_k_ci_low": row.pass_at_k_ci_low,
            "pass_at_k_ci_high": row.pass_at_k_ci_high,
            "all_scored_pass_count": row.all_scored_pass_count,
            "all_scored_pass_rate": row.all_scored_pass_rate,
            "mixed_count": row.mixed_count,
            "mixed_rate": row.mixed_rate,
            "failed_task_count": row.failed_task_count,
            "scored_task_count": row.scored_task_count,
            "error_trial_count": row.error_trial_count,
            "total_cost_usd": row.total_cost_usd,
            "wall_min": "" if row.wall_min is None else row.wall_min,
        }
        for row in summaries
    ]

    model_pass_scores = {
        summary.job_name: {
            task_name: 1.0 if outcome.scored_rewards and any(reward >= 1.0 for reward in outcome.scored_rewards) else 0.0
            for task_name, outcome in outcomes_by_job[summary.job_name].items()
            if outcome.scored_rewards
        }
        for summary in included
    }

    by_task_model: dict[str, list[tuple[str, float, float]]] = defaultdict(list)
    category_reward_values: dict[str, list[float]] = defaultdict(list)
    category_pass_values: dict[str, list[float]] = defaultdict(list)

    for summary in included:
        for task_name, outcome in outcomes_by_job[summary.job_name].items():
            if not outcome.scored_rewards:
                continue
            pass_at_k = 1.0 if any(reward >= 1.0 for reward in outcome.scored_rewards) else 0.0
            mean_reward = statistics.fmean(outcome.scored_rewards)
            by_task_model[task_name].append((summary.job_name, pass_at_k, mean_reward))

    task_rows: list[dict[str, Any]] = []
    for task_name, values in sorted(by_task_model.items()):
        meta = task_metadata.get(task_name) or TaskMeta(task_name, "unknown", "unknown", [])
        pass_scores = [value[1] for value in values]
        mean_rewards = [value[2] for value in values]
        task_binary = []
        other_scores = []
        for job_name, task_pass, _ in values:
            task_binary.append(task_pass)
            other = [score for other_task, score in model_pass_scores.get(job_name, {}).items() if other_task != task_name]
            other_scores.append(statistics.fmean(other) if other else 0.0)
        discr = pearson(task_binary, other_scores)
        task_rows.append(
            {
                "task": task_name,
                "category": meta.category,
                "difficulty": meta.difficulty,
                "n_models_scored": len(values),
                "mean_reward": statistics.fmean(mean_rewards),
                "models_pass_at_k": int(sum(pass_scores)),
                "models_pass_at_k_rate": statistics.fmean(pass_scores),
                "models_fail_at_k": int(len(pass_scores) - sum(pass_scores)),
                "task_floor": int(sum(pass_scores)) == 0,
                "task_ceiling": int(sum(pass_scores)) == len(pass_scores),
                "discrimination": "" if discr is None else discr,
            }
        )
        category_reward_values[meta.category].extend(mean_rewards)
        category_pass_values[meta.category].extend(pass_scores)

    category_rows = []
    for category, rewards in sorted(category_reward_values.items()):
        ci_low, ci_high = bootstrap_mean_interval(rewards, stable_seed(cohort_name, category, "category"))
        pass_scores = category_pass_values[category]
        category_rows.append(
            {
                "category": category,
                "n_model_task_cells": len(rewards),
                "mean_reward": statistics.fmean(rewards),
                "mean_reward_ci_low": ci_low,
                "mean_reward_ci_high": ci_high,
                "pass_at_k_rate": statistics.fmean(pass_scores),
                "pass_at_k_count": int(sum(pass_scores)),
            }
        )

    cohort_row = {
        "cohort": cohort_name,
        "provider": provider,
        "score_scope": score_scope,
        "run_dates": ";".join(
            sorted({str(row["run_date"]) for row in model_rows if row["run_date"]})
        ),
        "pattern": pattern,
        "expected_trials": expected_trials,
        "attempts_per_task": attempts_per_task,
        "n_jobs_total": len(summaries),
        "n_jobs_included": len(included),
        "n_jobs_excluded": len(excluded),
        "mean_model_pass_at_k": statistics.fmean(row.pass_at_k for row in included) if included else 0.0,
        "mean_model_pass_at_1": statistics.fmean(row.pass_at_1 for row in included) if included else 0.0,
        "mean_model_mean_reward": statistics.fmean(row.mean_reward for row in included) if included else 0.0,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / f"{cohort_name}_models.csv", model_rows, list(model_rows[0].keys()) if model_rows else ["cohort"])
    write_csv(out_dir / f"{cohort_name}_tasks.csv", task_rows, list(task_rows[0].keys()) if task_rows else ["task"])
    write_csv(out_dir / f"{cohort_name}_categories.csv", category_rows, list(category_rows[0].keys()) if category_rows else ["category"])
    write_csv(out_dir / f"{cohort_name}_cohort.csv", [cohort_row], list(cohort_row.keys()))
    render_headline_table(out_dir / "table_headline.tex", included, attempts_per_task, provider)
    render_exclusion_table(out_dir / "table_exclusions.tex", excluded)
    hardest_tasks = sorted(task_rows, key=lambda row: (row["models_pass_at_k_rate"], row["mean_reward"], row["task"]))[:6]
    render_task_table(out_dir / "table_hardest_tasks.tex", hardest_tasks, attempts_per_task)

    summary_json = {
        "cohort": cohort_row,
        "included_models": [row.job_name for row in included],
        "excluded_models": [{row.job_name: row.status_reason} for row in excluded],
        "best_model": included[0].model_label if included else "",
        "best_model_pass_at_k": included[0].pass_at_k_count if included else 0,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary_json, indent=2) + "\n")
    return summary_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs-dir", default="jobs")
    parser.add_argument("--tasks-dir", default="tasks")
    parser.add_argument("--pattern", default="full25-k4-open-*")
    parser.add_argument("--cohort-name", default="openrouter_k4_small")
    parser.add_argument("--expected-trials", type=int, default=100)
    parser.add_argument("--attempts-per-task", type=int, default=4)
    parser.add_argument("--max-error-rate", type=float, default=0.20)
    parser.add_argument("--out-dir", default="paper/generated")
    parser.add_argument("--provider", default="openrouter")
    parser.add_argument("--score-scope", default="core-25")
    parser.add_argument(
        "--exclude-task",
        action="append",
        default=[],
        help="task to drop from scored aggregates (repeatable); trials stay on disk",
    )
    args = parser.parse_args()

    summary = analyze(
        jobs_dir=Path(args.jobs_dir),
        tasks_dir=Path(args.tasks_dir),
        pattern=args.pattern,
        cohort_name=args.cohort_name,
        expected_trials=args.expected_trials,
        attempts_per_task=args.attempts_per_task,
        max_error_rate=args.max_error_rate,
        out_dir=Path(args.out_dir),
        provider=args.provider,
        score_scope=args.score_scope,
        excluded_tasks=frozenset(args.exclude_task),
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
