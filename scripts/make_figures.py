#!/usr/bin/env python3
"""Generate the paper's figures from the same CSVs that back its tables.

Figures are regenerated rather than drawn once, so they cannot drift from the
numbers in the text as more models finish.

Palette is the validated categorical set (blue / orange / violet): all six
checks pass, worst adjacent CVD separation dE 24.7. Colour never carries
identity alone -- every series is also direct-labelled or named on its axis.

Usage:
    python3 scripts/make_figures.py [--out-dir paper/figures]
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

BLUE, ORANGE, VIOLET = "#2a78d6", "#eb6834", "#4a3aa7"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#d8d7d2"

plt.rcParams.update(
    {
        "font.size": 8,
        "font.family": "serif",
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 200,
    }
)


def style(ax, xlabel="", ylabel=""):
    """Recessive grid and axes; the data should be the darkest thing present."""
    ax.grid(axis="x", color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)


def load(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open())) if path.exists() else []


def task_counts(root: Path = Path(".")) -> tuple[int, int]:
    """(core tasks, extension tasks) after retirements, read from configs."""
    def read(path: Path) -> set[str]:
        if not path.exists():
            return set()
        return {ln.strip() for ln in path.read_text().splitlines()
                if ln.strip() and not ln.startswith("#")}
    retired = read(root / "configs/retired_tasks.txt")
    core = read(root / "configs/core25_tasks.txt") - retired
    hard = read(root / "configs/v2_retained_tasks.txt") - retired
    return len(core), len(hard)


def fig_paired(generated: Path, out: Path) -> None:
    """Core vs extension per model: does the harder pack separate models?

    A dumbbell, because the job is the *change* within each entity across two
    conditions, and the gap is the quantity being read.
    """
    n_core, n_hard = task_counts()
    data = json.loads((generated / "paired_scopes.json").read_text())
    pairs = sorted(data["pairs"], key=lambda p: p["core_mean"] - p["hard_mean"])
    fig, ax = plt.subplots(figsize=(5.2, 0.28 * len(pairs) + 0.95))
    ys = range(len(pairs))
    for y, p in zip(ys, pairs):
        ax.plot([p["hard_mean"], p["core_mean"]], [y, y], color=GRID, linewidth=2.4, zorder=1)
        ax.scatter(p["core_mean"], y, s=42, color=BLUE, zorder=3, edgecolor="white", linewidth=0.8)
        ax.scatter(p["hard_mean"], y, s=42, color=ORANGE, zorder=3, edgecolor="white", linewidth=0.8)
    ax.set_yticks(list(ys))
    ax.set_yticklabels([f"{p['model']}" for p in pairs])
    ax.set_xlim(0.35, 1.06)
    ax.set_ylim(-0.8, len(pairs) - 0.2)
    ax.legend(
        handles=[Patch(facecolor=BLUE, label=f"{n_core}-task core"),
                 Patch(facecolor=ORANGE, label=f"{n_hard}-task extension")],
        loc="lower center", bbox_to_anchor=(0.5, 1.0), frameon=False, ncol=2, fontsize=7.5,
    )
    style(ax, xlabel="mean reward (fraction of individual attempts correct)")
    fig.tight_layout()
    fig.savefig(out / "fig_paired_scopes.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_failures(generated: Path, out: Path) -> None:
    """How runs fail. Stacked bars: the composition is the message."""
    rows = load(generated / "failure_modes_openrouter_k4.csv")
    if not rows:
        return
    order = ["missing", "malformed", "wrong_value"]
    labels = {
        "missing": "no output produced",
        "malformed": "output malformed",
        "wrong_value": "well-formed, wrong values",
    }
    colors = {"missing": VIOLET, "malformed": BLUE, "wrong_value": ORANGE}

    per_task: dict[str, Counter] = {}
    for r in rows:
        per_task.setdefault(r["task"], Counter())[r["bucket"]] += 1
    top = sorted(per_task.items(), key=lambda kv: -sum(kv[1].values()))[:10]
    top = sorted(top, key=lambda kv: sum(kv[1].values()))

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(6.6, 2.75), gridspec_kw={"width_ratios": [1, 1.5]}
    )

    totals = Counter(r["bucket"] for r in rows)
    n = sum(totals.values())
    left = 0.0
    for bucket in order:
        share = 100 * totals[bucket] / n
        ax1.barh([0], [share], left=left, height=0.5, color=colors[bucket],
                 edgecolor="white", linewidth=1.6, zorder=2)
        ax1.text(left + share / 2, 0, f"{share:.0f}%", ha="center", va="center",
                 color="white", fontsize=8.5, fontweight="bold")
        left += share
    ax1.set_yticks([])
    ax1.set_xlim(0, 100)
    ax1.set_title(f"All {n} scored failures", fontsize=8.5, color=INK, pad=8)
    ax1.set_xlabel("share of failures (%)")
    ax1.grid(axis="x", color=GRID, linewidth=0.6, zorder=0)
    ax1.set_axisbelow(True)
    ax1.legend(
        handles=[Patch(facecolor=colors[b], label=labels[b]) for b in order],
        loc="upper center", bbox_to_anchor=(0.5, -0.42), frameon=False, fontsize=7.5,
    )

    ys = range(len(top))
    for y, (task, counts) in zip(ys, top):
        left = 0
        for bucket in order:
            v = counts.get(bucket, 0)
            if not v:
                continue
            ax2.barh([y], [v], left=left, height=0.62, color=colors[bucket],
                     edgecolor="white", linewidth=1.4, zorder=2)
            left += v
    ax2.set_yticks(list(ys))
    ax2.set_yticklabels([t for t, _ in top], fontsize=7)
    ax2.set_title("Ten tasks with the most failures", fontsize=8.5, color=INK, pad=8)
    ax2.set_xlabel("scored failures")
    ax2.grid(axis="x", color=GRID, linewidth=0.6, zorder=0)
    ax2.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(out / "fig_failure_modes.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_cost(generated: Path, out: Path) -> None:
    """Price against capability. Openness and cost are independent axes."""
    rows = [r for r in load(generated / "openrouter-addon-hard8"
                            / "openrouter_addon_hard8_models.csv")
            if r["status"] == "included"]
    if not rows:
        return
    # Weight availability cannot be derived from run receipts, so it is declared
    # in configs/model_licences.tsv and must be confirmed by the authors.
    licences = {}
    lic_path = Path("configs/model_licences.tsv")
    if lic_path.exists():
        for line in lic_path.read_text().splitlines():
            if not line.strip() or line.startswith(("#", "slug")):
                continue
            slug, access = line.split("\t")[:2]
            licences[slug] = access.strip()
    slug_of = {r["model_label"]: r["job_name"].rsplit("-k4-", 1)[-1] for r in rows}
    open_weight = {label for label, slug in slug_of.items()
                   if licences.get(slug) == "open-weight"}
    fig, ax = plt.subplots(figsize=(5.2, 2.9))
    for r in rows:
        cost, mean = float(r["total_cost_usd"]), float(r["mean_reward"])
        is_open = r["model_label"] in open_weight
        ax.scatter(cost, mean, s=70, zorder=3,
                   color=BLUE if is_open else ORANGE,
                   marker="o" if is_open else "D",
                   edgecolor="white", linewidth=0.9)
        ax.annotate(r["model_label"], (cost, mean), textcoords="offset points",
                    xytext=(7, 5), fontsize=7, color=INK)
    ax.scatter([], [], s=70, color=BLUE, marker="o", label="open-weight")
    ax.scatter([], [], s=70, color=ORANGE, marker="D", label="proprietary")
    ax.legend(loc="lower right", frameon=False, fontsize=7.5)
    ax.set_xlim(0, max(float(r["total_cost_usd"]) for r in rows) * 1.35)
    ax.set_ylim(0.42, 1.0)
    style(ax, xlabel="billed cost for the 32-trial extension sweep (USD)",
          ylabel="mean reward")
    fig.tight_layout()
    fig.savefig(out / "fig_cost_capability.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated-dir", type=Path, default=Path("paper/generated"))
    parser.add_argument("--out-dir", type=Path, default=Path("paper/figures"))
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    fig_paired(args.generated_dir, args.out_dir)
    fig_failures(args.generated_dir, args.out_dir)
    fig_cost(args.generated_dir, args.out_dir)
    made = sorted(p.name for p in args.out_dir.glob("*.pdf"))
    print("wrote:", ", ".join(made) if made else "(nothing)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
