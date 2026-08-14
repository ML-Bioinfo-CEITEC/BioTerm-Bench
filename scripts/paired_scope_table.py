#!/usr/bin/env python3
"""Emit the paired core-25 vs hard-8 comparison for models that ran both scopes.

Comparing hard-subset scores from one cohort against core-25 scores from
another would confound task difficulty with model set and serving stack, so the
only admissible comparison is within a model on one provider. This script finds
models with an *included* job in both scopes of the same provider and reports
how each metric moves between them.

Outputs a LaTeX table plus a JSON summary so the prose can cite the aggregate
without anyone retyping it as new models land.

Usage:
    python3 scripts/paired_scope_table.py
    python3 scripts/paired_scope_table.py --generated-dir paper/generated
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path

#: (provider label, hard-subset models CSV, core-25 models CSV)
COHORTS = [
    (
        "e-INFRA",
        "einfra-hard8/einfra_k4_hard8_models.csv",
        "einfra-core25/einfra_k4_core25_models.csv",
    ),
    (
        "OpenRouter",
        "openrouter-addon-hard8/openrouter_addon_hard8_models.csv",
        "openrouter-addon-core25/openrouter_addon_core25_models.csv",
    ),
]


def load_included(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open() as fh:
        return {r["model_label"]: r for r in csv.DictReader(fh) if r["status"] == "included"}


def ratio(row: dict[str, str], count_key: str, denom_key: str) -> float | None:
    denom = int(row[denom_key])
    return int(row[count_key]) / denom if denom else None


def latex_escape(text: str) -> str:
    return text.replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")


def collect(generated_dir: Path) -> list[dict[str, object]]:
    pairs: list[dict[str, object]] = []
    for provider, hard_rel, core_rel in COHORTS:
        hard = load_included(generated_dir / hard_rel)
        core = load_included(generated_dir / core_rel)
        for model in sorted(set(hard) & set(core)):
            h, c = hard[model], core[model]
            entry = {
                "provider": provider,
                "model": model,
                "core_mean": float(c["mean_reward"]),
                "hard_mean": float(h["mean_reward"]),
                "core_pass_at_1": ratio(c, "pass_at_1_count", "pass_at_1_scored_denominator"),
                "hard_pass_at_1": ratio(h, "pass_at_1_count", "pass_at_1_scored_denominator"),
                "core_pass_at_k": ratio(c, "pass_at_k_count", "pass_at_k_scored_denominator"),
                "hard_pass_at_k": ratio(h, "pass_at_k_count", "pass_at_k_scored_denominator"),
            }
            for metric in ("mean", "pass_at_1", "pass_at_k"):
                core_v, hard_v = entry[f"core_{metric}"], entry[f"hard_{metric}"]
                entry[f"drop_{metric}"] = (
                    None if core_v is None or hard_v is None else core_v - hard_v
                )
            pairs.append(entry)
    return pairs


def summarize(pairs: list[dict[str, object]]) -> dict[str, object]:
    drops_mean = [p["drop_mean"] for p in pairs if p["drop_mean"] is not None]
    drops_k = [p["drop_pass_at_k"] for p in pairs if p["drop_pass_at_k"] is not None]
    summary: dict[str, object] = {
        "n_paired_models": len(pairs),
        "providers": sorted({str(p["provider"]) for p in pairs}),
        "mean_drop_mean_reward": statistics.fmean(drops_mean) if drops_mean else None,
        "mean_drop_pass_at_k": statistics.fmean(drops_k) if drops_k else None,
    }
    md, dk = summary["mean_drop_mean_reward"], summary["mean_drop_pass_at_k"]
    summary["reliability_vs_solvability_ratio"] = (
        md / dk if md is not None and dk not in (None, 0) else None
    )
    return summary


def render_table(pairs: list[dict[str, object]]) -> str:
    lines = [
        r"\begin{tabular}{llrrrrrr}",
        r"\toprule",
        (
            r"& & \multicolumn{2}{c}{mean reward} & \multicolumn{2}{c}{pass@1} "
            r"& \multicolumn{2}{c}{pass@4} \\"
        ),
        r"\cmidrule(lr){3-4}\cmidrule(lr){5-6}\cmidrule(lr){7-8}",
        r"Provider & Model & core & hard & core & hard & core & hard \\",
        r"\midrule",
    ]
    for p in pairs:
        def fmt(value: object) -> str:
            return "--" if value is None else f"{float(value):.3f}"

        lines.append(
            f"{latex_escape(str(p['provider']))} & {latex_escape(str(p['model']))} "
            f"& {fmt(p['core_mean'])} & {fmt(p['hard_mean'])} "
            f"& {fmt(p['core_pass_at_1'])} & {fmt(p['hard_pass_at_1'])} "
            f"& {fmt(p['core_pass_at_k'])} & {fmt(p['hard_pass_at_k'])} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated-dir", type=Path, default=Path("paper/generated"))
    args = parser.parse_args()

    pairs = collect(args.generated_dir)
    if not pairs:
        print("no models have an included job in both scopes yet")
        return 1

    summary = summarize(pairs)
    (args.generated_dir / "table_paired_scopes.tex").write_text(render_table(pairs))
    (args.generated_dir / "paired_scopes.json").write_text(
        json.dumps({"summary": summary, "pairs": pairs}, indent=2) + "\n"
    )
    # Emit the aggregates as macros so the prose never carries a hand-typed
    # figure that goes stale the next time a model finishes.
    (args.generated_dir / "paired_scopes_macros.tex").write_text(
        "\n".join(
            [
                r"%% Generated by scripts/paired_scope_table.py -- do not edit.",
                rf"\newcommand{{\pairedModelCount}}{{{summary['n_paired_models']}}}",
                rf"\newcommand{{\pairedDropMeanReward}}{{{summary['mean_drop_mean_reward']:.3f}}}",
                rf"\newcommand{{\pairedDropPassAtK}}{{{summary['mean_drop_pass_at_k']:.3f}}}",
                rf"\newcommand{{\pairedDropRatio}}{{{summary['reliability_vs_solvability_ratio']:.1f}}}",
            ]
        )
        + "\n"
    )

    print(f"paired models: {summary['n_paired_models']} across {', '.join(summary['providers'])}")
    print(f"  mean drop in mean reward : {summary['mean_drop_mean_reward']:.3f}")
    print(f"  mean drop in pass@4      : {summary['mean_drop_pass_at_k']:.3f}")
    if summary["reliability_vs_solvability_ratio"]:
        print(f"  ratio                    : {summary['reliability_vs_solvability_ratio']:.1f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
