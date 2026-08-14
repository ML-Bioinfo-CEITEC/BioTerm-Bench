#!/usr/bin/env python3
"""Poster-scale redraws of the BioTerm-Bench paper figures.

Same CSV/JSON inputs as scripts/make_figures.py and scripts/hardware_tiers.py,
so the poster cannot drift from the manuscript. The only differences are
presentational: figures are drawn at their *final printed size* (A0 three-column
card width = 8.8 in), so point sizes here are real point sizes on the board.

Usage:
    python3 make_poster_figures.py            # writes poster/figures/*.pdf
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D  # noqa: F401  (legend proxies)

# ---------------------------------------------------------------- design tokens
BLUE, ORANGE, VIOLET = "#2A78D6", "#EB6834", "#4A3AA7"
INK, MUTED, GRID = "#14181F", "#5A5F66", "#DCDEE2"
NAVY = "#102A43"

COLW = 8.80  # in -- printed width of one poster card's inner text block

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Carlito", "Liberation Sans", "DejaVu Sans"],
        "font.size": 16,
        "axes.edgecolor": MUTED,
        "axes.linewidth": 1.1,
        "axes.labelcolor": INK,
        "axes.labelsize": 18,
        "text.color": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelsize": 16,
        "ytick.labelsize": 16,
        "xtick.major.width": 1.1,
        "ytick.major.width": 1.1,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.fontsize": 16,
        "figure.dpi": 200,
        "pdf.fonttype": 42,
    }
)

GEN = Path("paper/generated")
OUT = Path("paper/figures")

#: The summarizer title-cases job slugs, which mangles vendor capitalisation.
#: Cosmetic only -- never used to join data, so it cannot reorder anything.
PRETTY = {
    "Gpt Oss 120B": "GPT-OSS 120B",
    "Glm 5.2": "GLM 5.2",
    "Gemma4": "Gemma 4",
    "Deepseek V4 Flash": "DeepSeek V4 Flash",
    "Deepseek V4 Flash Thinking": "DeepSeek V4 Flash (thinking)",
    "Qwen3.5 Int4": "Qwen3.5 int4",
    "GPT-OSS-120B": "GPT-OSS 120B",
}


def pretty(name: str) -> str:
    return PRETTY.get(name, name)


def load(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open())) if path.exists() else []


def task_counts(root: Path = Path(".")) -> tuple[int, int]:
    def read(p: Path) -> set[str]:
        if not p.exists():
            return set()
        return {ln.strip() for ln in p.read_text().splitlines()
                if ln.strip() and not ln.startswith("#")}
    retired = read(root / "configs/retired_tasks.txt")
    return (len(read(root / "configs/core25_tasks.txt") - retired),
            len(read(root / "configs/v2_retained_tasks.txt") - retired))


def grid(ax, axis="x"):
    ax.grid(axis=axis, color=GRID, linewidth=0.9, zorder=0)
    ax.set_axisbelow(True)


# ------------------------------------------------------------------ figure 1
def fig_paired() -> None:
    """Dumbbell: core vs extension mean reward, one row per model.

    The quantity being read is the *gap*, so the connector is drawn heavier
    than in the paper version and the two ends are direct-labelled at the top.
    """
    n_core, n_hard = task_counts()
    pairs = json.loads((GEN / "paired_scopes.json").read_text())["pairs"]
    pairs = sorted(pairs, key=lambda p: p["core_mean"] - p["hard_mean"])

    fig, ax = plt.subplots(figsize=(COLW, 0.455 * len(pairs) + 1.50))
    for y, p in enumerate(pairs):
        lo, hi = sorted((p["core_mean"], p["hard_mean"]))
        worse = p["hard_mean"] < p["core_mean"]
        ax.plot([lo, hi], [y, y], color=ORANGE if worse else BLUE,
                alpha=0.28, linewidth=7.0, solid_capstyle="round", zorder=1)
        ax.scatter(p["core_mean"], y, s=210, color=BLUE, zorder=3,
                   edgecolor="white", linewidth=2.0)
        ax.scatter(p["hard_mean"], y, s=210, color=ORANGE, zorder=3,
                   edgecolor="white", linewidth=2.0)

    ax.set_yticks(range(len(pairs)))
    ax.set_yticklabels([pretty(p["model"]) for p in pairs], fontsize=16.5, color=INK)
    ax.set_xlim(0.36, 1.055)
    ax.set_ylim(-0.85, len(pairs) - 0.15)
    ax.tick_params(axis="y", length=0, pad=8)
    ax.spines["left"].set_visible(False)
    ax.legend(
        handles=[Line2D([], [], marker="o", linestyle="", markersize=13,
                        markerfacecolor=BLUE, markeredgecolor="white",
                        markeredgewidth=1.6, label=f"{n_core}-task core"),
                 Line2D([], [], marker="o", linestyle="", markersize=13,
                        markerfacecolor=ORANGE, markeredgecolor="white",
                        markeredgewidth=1.6, label=f"{n_hard}-task extension")],
        loc="lower center", bbox_to_anchor=(0.5, 1.005), frameon=False,
        ncol=2, handletextpad=0.3, columnspacing=2.4, fontsize=17,
    )
    grid(ax, "x")
    ax.set_xlabel("mean reward  (fraction of individual attempts correct)",
                  fontsize=17.5, labelpad=9)
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    fig.savefig(OUT / "pfig_paired_scopes.pdf")
    plt.close(fig)


# ------------------------------------------------------------------ figure 2
def fig_failures() -> None:
    """How runs fail: composition first, then where it lands.

    Stacked bars because the composition is the message; the top strip is the
    poster's actual headline, so it is given its own full-width band.
    """
    rows = load(GEN / "failure_modes_openrouter_k4.csv")
    if not rows:
        raise SystemExit("failure_modes CSV missing")

    order = ["missing", "malformed", "wrong_value"]
    labels = {"missing": "no output at all",
              "malformed": "output malformed",
              "wrong_value": "well-formed, WRONG VALUES"}
    colors = {"missing": VIOLET, "malformed": BLUE, "wrong_value": ORANGE}

    per_task: dict[str, Counter] = {}
    for r in rows:
        per_task.setdefault(r["task"], Counter())[r["bucket"]] += 1
    top = sorted(per_task.items(), key=lambda kv: -sum(kv[1].values()))[:10]
    top = sorted(top, key=lambda kv: sum(kv[1].values()))

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(COLW, 6.50), gridspec_kw={"height_ratios": [1, 3.4], "hspace": 0.40}
    )

    totals = Counter(r["bucket"] for r in rows)
    n = sum(totals.values())
    left = 0.0
    for bucket in order:
        share = 100 * totals[bucket] / n
        ax1.barh([0], [share], left=left, height=1.0, color=colors[bucket],
                 edgecolor="white", linewidth=3.0, zorder=2)
        ax1.text(left + share / 2, 0.06, f"{share:.0f}%", ha="center", va="center",
                 color="white", fontsize=27, fontweight="bold")
        ax1.text(left + share / 2, -0.86, labels[bucket], ha="center", va="top",
                 color=colors[bucket], fontsize=14.5, fontweight="bold", wrap=True)
        left += share
    ax1.set_xlim(0, 100)
    ax1.set_ylim(-1.5, 0.7)
    ax1.axis("off")
    ax1.set_title(f"All {n} scored failures in the core cohort",
                  fontsize=17.5, color=MUTED, pad=12, loc="left")

    for y, (task, counts) in enumerate(top):
        left = 0
        for bucket in order:
            v = counts.get(bucket, 0)
            if not v:
                continue
            ax2.barh([y], [v], left=left, height=0.68, color=colors[bucket],
                     edgecolor="white", linewidth=2.2, zorder=2)
            left += v
    ax2.set_yticks(range(len(top)))
    ax2.set_yticklabels([t for t, _ in top], fontsize=15,
                        fontfamily="DejaVu Sans Mono", color=INK)
    ax2.tick_params(axis="y", length=0, pad=8)
    ax2.spines["left"].set_visible(False)
    ax2.set_title("Ten tasks contributing the most failures", fontsize=17.5,
                  color=MUTED, pad=12, loc="left")
    ax2.set_xlabel("scored failures", fontsize=17.5, labelpad=8)
    grid(ax2, "x")
    # tight_layout cannot measure the axis-off strip, so margins are explicit;
    # left is set by the longest monospaced task name.
    fig.subplots_adjust(left=0.325, right=0.995, top=0.90, bottom=0.105)
    # The composition strip has no y labels, so it takes the full figure width.
    p1 = ax1.get_position()
    ax1.set_position((0.012, p1.y0, 0.983, p1.height))
    fig.savefig(OUT / "pfig_failure_modes.pdf")
    plt.close(fig)


# ------------------------------------------------------------------ figure 3
BYTES_PER_PARAM = {"bf16": 2.0, "fp16": 2.0, "fp8": 1.0, "int4": 0.5, "mxfp4": 0.5}
TIERS = [(24, "A", "laptop or workstation"), (141, "B", "one datacentre GPU"),
         (600, "C", "2-4 GPU server"), (1200, "D", "full 8-GPU node"),
         (float("inf"), "E", "multi-node cluster")]
LABEL_FIXES = {"GPT-OSS-120B": "Gpt Oss 120B", "Gemma 4": "Gemma4",
               "GLM 5.2": "Glm 5.2", "DeepSeek V4 Flash": "Deepseek V4 Flash",
               "DeepSeek V4 Flash Thinking": "Deepseek V4 Flash Thinking"}


def _parse_params(text: str) -> float | None:
    text = text.strip().lstrip("A")
    if text.endswith("T"):
        return float(text[:-1]) * 1000
    if text.endswith("B"):
        return float(text[:-1])
    return None


def _tier_for(weight_gb: float, params_b: float) -> tuple[str, str]:
    if params_b * 0.5 <= 24:
        return "A", "laptop or workstation"
    for limit, tid, label in TIERS:
        if weight_gb <= limit:
            return tid, label
    return "E", "multi-node cluster"


def fig_hardware() -> None:
    """Capability against the hardware needed to host it, log-x."""
    manifest = list(csv.DictReader(open("configs/einfra_panel.tsv"), delimiter="\t"))
    scores = {r["model_label"]: float(r["mean_reward"])
              for r in load(GEN / "einfra-hard8" / "einfra_k4_hard8_models.csv")
              if r["status"] == "included"}
    models = []
    for row in manifest:
        params, per = _parse_params(row["total_params"]), BYTES_PER_PARAM.get(row["quantization"])
        if params is None or per is None:
            continue
        gb = params * per
        tid, tlabel = _tier_for(gb, params)
        models.append({"name": row["display_name"], "gb": gb, "tier": tid,
                       "tlabel": tlabel,
                       "score": scores.get(LABEL_FIXES.get(row["display_name"],
                                                           row["display_name"]))})
    scored = [m for m in sorted(models, key=lambda d: d["gb"]) if m["score"] is not None]

    colour = {"A": BLUE, "B": ORANGE, "C": VIOLET, "D": MUTED, "E": INK}
    # Only the three models the argument names are labelled individually. The
    # top band is annotated as a group instead: six overlapping labels would
    # cost more legibility than the model identities buy, and the tier table
    # printed beside this panel already names every point.
    offsets = {
        "Qwen3.5 122B": (0, -38, "center"),
        "GPT-OSS 120B": (0, -38, "center"),
        "Gemma 4": (0, 23, "center"),
    }
    fig, ax = plt.subplots(figsize=(COLW, 4.78))

    band = [m for m in scored if m["score"] >= 0.90]
    lo_gb, hi_gb = min(m["gb"] for m in band), max(m["gb"] for m in band)
    lo_s, hi_s = min(m["score"] for m in band), max(m["score"] for m in band)
    ax.axhspan(lo_s - 0.045, hi_s + 0.045, color=GRID, alpha=0.5, zorder=0)
    ax.text(0.5, 1.10, f"{len(band)} models spanning {lo_gb:.0f} GB to "
                       f"{hi_gb/1000:.1f} TB — all score {lo_s:.2f}–{hi_s:.2f}",
            transform=ax.transAxes, ha="center", va="center",
            fontsize=15.5, color=MUTED, style="italic", zorder=5)
    ax.text(0.5, 1.035, f"{hi_gb/lo_gb:.0f}$\\times$ the hardware, no measurable gain",
            transform=ax.transAxes, ha="center", va="center",
            fontsize=15.5, color=ORANGE, fontweight="bold", zorder=5)

    for m in scored:
        name = pretty(m["name"])
        # The tier letter rides inside its own marker, so the panel needs no
        # legend and the tier column of the adjacent table is the only key.
        ax.scatter(m["gb"], m["score"], s=580, zorder=3,
                   color=colour.get(m["tier"], MUTED), edgecolor="white", linewidth=2.2)
        ax.text(m["gb"], m["score"], m["tier"], ha="center", va="center",
                color="white", fontsize=15, fontweight="bold", zorder=4)
        if name in offsets:
            dx, dy, ha = offsets[name]
            ax.annotate(name, (m["gb"], m["score"]), textcoords="offset points",
                        xytext=(dx, dy), fontsize=15, color=INK, ha=ha, zorder=5)
    ax.set_xscale("log")
    ax.set_xlim(33, 4600)
    ax.set_ylim(0.32, 1.06)
    grid(ax, "both")
    ax.set_xlabel("weight memory at served precision (GB, log scale)",
                  fontsize=17.5, labelpad=9)
    ax.set_ylabel("mean reward, extension", fontsize=17.5, labelpad=9)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(OUT / "pfig_hardware_vs_score.pdf")
    plt.close(fig)


# ------------------------------------------------------------------ figure 4
def fig_cost() -> None:
    """Price against capability. Openness and cost are independent axes."""
    rows = [r for r in load(GEN / "openrouter-addon-hard8"
                            / "openrouter_addon_hard8_models.csv")
            if r["status"] == "included"]
    licences = {}
    for line in Path("configs/model_licences.tsv").read_text().splitlines():
        if not line.strip() or line.startswith(("#", "slug")):
            continue
        slug, access = line.split("\t")[:2]
        licences[slug] = access.strip()
    slug_of = {r["model_label"]: r["job_name"].rsplit("-k4-", 1)[-1] for r in rows}
    open_weight = {lab for lab, s in slug_of.items() if licences.get(s) == "open-weight"}

    offsets = {"GPT-5.6 Luna": (0, -36, "center"),
               "Inkling Small": (0, -36, "center"),
               "Muse Glimmer 30B": (0, -36, "center"),
               "Qwen 3.6 35B A3B": (16, -7, "left"),
               "Nemotron 3.5 Lightning": (16, -7, "left")}
    fig, ax = plt.subplots(figsize=(COLW, 4.08))
    # The spread along y is small and the spread along x is the story, so the
    # cheapest/dearest tie at 1.000 is bracketed rather than left to be inferred.
    by_cost = sorted((float(r["total_cost_usd"]) for r in rows
                      if float(r["mean_reward"]) == 1.0))
    if len(by_cost) >= 2:
        lo, hi = by_cost[0], by_cost[-1]
        ax.annotate("", xy=(lo, 1.045), xytext=(hi, 1.045),
                    arrowprops=dict(arrowstyle="<->", color=MUTED, linewidth=1.6))
        ax.text((lo + hi) / 2, 1.062, f"{hi / lo:.0f}$\\times$ the price, identical score",
                ha="center", va="bottom", fontsize=15.5, color=MUTED, style="italic")
    for r in rows:
        cost, mean = float(r["total_cost_usd"]), float(r["mean_reward"])
        is_open = r["model_label"] in open_weight
        ax.scatter(cost, mean, s=250, zorder=3, color=BLUE if is_open else ORANGE,
                   marker="o" if is_open else "D", edgecolor="white", linewidth=2.0)
        dx, dy, ha = offsets.get(r["model_label"], (10, 12, "left"))
        ax.annotate(pretty(r["model_label"]), (cost, mean), textcoords="offset points",
                    xytext=(dx, dy), fontsize=14.5, color=INK, ha=ha)
    ax.scatter([], [], s=200, color=BLUE, marker="o", label="open weights")
    ax.scatter([], [], s=200, color=ORANGE, marker="D", label="proprietary")
    ax.legend(loc="lower right", frameon=False, fontsize=15.5)
    ax.set_xlim(-0.02, max(float(r["total_cost_usd"]) for r in rows) * 1.28)
    ax.set_ylim(0.44, 1.16)
    grid(ax, "both")
    ax.set_xlabel("billed cost of the whole 28-trial extension sweep (USD)",
                  fontsize=17.5, labelpad=9)
    ax.set_ylabel("mean reward", fontsize=17.5, labelpad=9)
    fig.tight_layout()
    fig.savefig(OUT / "pfig_cost_capability.pdf")
    plt.close(fig)


# ------------------------------------------------------------------- tables
def table_headline() -> None:
    """Core-25 leaderboard, poster columns only.

    Derived from the same per-model CSV as generated/table_headline.tex; the
    'mixed' and cost columns are dropped because seven columns only fit on an
    A0 card by shrinking the type below reading distance.
    """
    rows = [r for r in load(GEN / "openrouter_k4_small_models.csv")
            if r["status"] == "included"]
    rows.sort(key=lambda r: -float(r["mean_reward"]))
    out = [r"\begin{tabular}{@{}lrrrr@{}}", r"\toprule",
           r"Model & \makebox[0pt][r]{mean reward} & pass@1 & all scored & pass@4 \\",
           r"\midrule"]
    for r in rows:
        n = r["scored_task_count"]
        out.append(
            f"{r['model_label']} & {float(r['mean_reward']):.3f} "
            f"& {r['pass_at_1_count']}/{r['pass_at_1_scored_denominator']} "
            f"& {r['all_scored_pass_count']}/{n} "
            f"& {r['pass_at_k_count']}/{r['pass_at_k_scored_denominator']} \\\\")
    out += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "poster_table_headline.tex").write_text("\n".join(out) + "\n")


def table_hardware() -> None:
    """Hardware ladder, poster columns only (precision folded into the note)."""
    manifest = list(csv.DictReader(open("configs/einfra_panel.tsv"), delimiter="\t"))
    out = [r"\begin{tabular}{@{}llrl@{}}", r"\toprule",
           r"Model & Total (active) & GB & Hardware needed \\", r"\midrule"]
    entries = []
    for row in manifest:
        params, per = _parse_params(row["total_params"]), BYTES_PER_PARAM.get(row["quantization"])
        if params is None or per is None:
            continue
        gb = params * per
        tid, tlabel = _tier_for(gb, params)
        active = "" if row["active_params"] in ("unknown", row["total_params"]) \
            else f" ({row['active_params']})"
        shown = f"{params/1000:.1f}T" if params >= 1000 else f"{params:.0f}B"
        entries.append((gb, f"{pretty(row['display_name'])} & {shown}{active} "
                            f"& {gb + 0.4:.0f} & {tid}: {tlabel} \\\\"))
    out += [line for _, line in sorted(entries)]
    out += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "poster_table_hardware.tex").write_text("\n".join(out) + "\n")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    fig_paired()
    fig_failures()
    fig_hardware()
    fig_cost()
    table_headline()
    table_hardware()
    for p in sorted(GEN.glob("poster_table_*.tex")):
        print(f"  wrote {p}")
    for p in sorted(OUT.glob("*.pdf")):
        print(f"  wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
