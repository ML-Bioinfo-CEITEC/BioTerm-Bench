#!/usr/bin/env python3
"""Map each evaluated model to the hardware a laboratory needs to self-host it.

Weight memory is computed as (total parameters) x (bytes per parameter at the
served precision). This is a floor, not a deployment spec: KV cache for a
256K-1M context, activations, and runtime buffers add substantially on top, and
mixture-of-experts routing needs the *whole* weight set resident even though
only the active parameters run per token.

The method is anchored against a published figure: Kimi K3's released MXFP4
weights are reported at ~1.4 TB, which is what 2.8T x 0.5 bytes gives.

Emits a LaTeX table and a size-versus-capability figure.

Usage:
    python3 scripts/hardware_tiers.py
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

BYTES_PER_PARAM = {"bf16": 2.0, "fp16": 2.0, "fp8": 1.0, "int4": 0.5, "mxfp4": 0.5}

#: (upper bound on weight GB, short tier id, what a lab actually needs)
TIERS = [
    (24, "A", "laptop or workstation"),
    (141, "B", "one datacentre GPU"),
    (600, "C", "2--4 GPU server"),
    (1200, "D", "full 8-GPU node"),
    (float("inf"), "E", "multi-node cluster"),
]

BLUE, ORANGE, VIOLET = "#2a78d6", "#eb6834", "#4a3aa7"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#d8d7d2"

#: e-INFRA manifest display names vs summarizer labels.
LABEL_FIXES = {
    "GPT-OSS-120B": "Gpt Oss 120B",
    "Gemma 4": "Gemma4",
    "GLM 5.2": "Glm 5.2",
    "DeepSeek V4 Flash": "Deepseek V4 Flash",
    "DeepSeek V4 Flash Thinking": "Deepseek V4 Flash Thinking",
}


def parse_params(text: str) -> float | None:
    text = text.strip().lstrip("A")
    if text.endswith("T"):
        return float(text[:-1]) * 1000
    if text.endswith("B"):
        return float(text[:-1])
    return None


def tier_for(weight_gb: float, params_b: float) -> tuple[str, str]:
    # A dense model small enough to 4-bit quantise onto consumer hardware belongs
    # in tier A even if the served checkpoint is bf16.
    if params_b * 0.5 <= 24:
        return "A", "laptop or workstation"
    for limit, tid, label in TIERS:
        if weight_gb <= limit:
            return tid, label
    return "E", "multi-node cluster"


def collect(root: Path) -> list[dict[str, object]]:
    manifest = list(csv.DictReader((root / "configs/einfra_panel.tsv").open(), delimiter="\t"))
    score_path = root / "paper/generated/einfra-hard8/einfra_k4_hard8_models.csv"
    scores = {}
    if score_path.exists():
        scores = {r["model_label"]: float(r["mean_reward"])
                  for r in csv.DictReader(score_path.open()) if r["status"] == "included"}
    out = []
    for row in manifest:
        params = parse_params(row["total_params"])
        per = BYTES_PER_PARAM.get(row["quantization"])
        if params is None or per is None:
            continue
        gb = params * per
        tid, tlabel = tier_for(gb, params)
        label = LABEL_FIXES.get(row["display_name"], row["display_name"])
        out.append({
            "name": row["display_name"],
            "params_b": params,
            "active": row["active_params"],
            "quant": row["quantization"],
            "weight_gb": gb,
            "tier": tid,
            "tier_label": tlabel,
            "score": scores.get(label),
        })
    return sorted(out, key=lambda d: d["weight_gb"])


def render_table(models: list[dict[str, object]], out: Path) -> None:
    lines = [
        r"\begin{tabular}{llrrl}",
        r"\toprule",
        r"Model & Total (active) & Precision & Weights (GB) & Hardware needed \\",
        r"\midrule",
    ]
    for m in models:
        active = "" if m["active"] in ("unknown", m["name"]) else f" ({m['active']})"
        params = f"{m['params_b']/1000:.1f}T" if m["params_b"] >= 1000 else f"{m['params_b']:.0f}B"
        lines.append(
            f"{m['name']} & {params}{active} & \\texttt{{{m['quant']}}} "
            f"& {m['weight_gb']:.0f} & {m['tier']}: {m['tier_label']} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    out.write_text("\n".join(lines) + "\n")


def render_figure(models: list[dict[str, object]], out: Path) -> None:
    scored = [m for m in models if m["score"] is not None]
    if not scored:
        return
    colour = {"A": BLUE, "B": ORANGE, "C": VIOLET, "D": MUTED, "E": INK}
    fig, ax = plt.subplots(figsize=(5.6, 3.1))
    # Alternate label placement: several models sit within a narrow band of both
    # size and score, and a fixed offset stacks their labels on top of each other.
    offsets = {
        "Mistral Medium 3.5": (7, 9, "left"),
        "DeepSeek V4 Flash": (8, -13, "left"),
        "DeepSeek V4 Flash Thinking": (0, 10, "center"),
        "Qwen3.5 Int4": (-2, -15, "center"),
        "Qwen3.5 122B": (0, -15, "center"),
        "GPT-OSS-120B": (0, -15, "center"),
    }
    for m in scored:
        ax.scatter(m["weight_gb"], m["score"], s=72, zorder=3,
                   color=colour.get(m["tier"], MUTED), edgecolor="white", linewidth=0.9)
        dx, dy, ha = offsets.get(m["name"], (0, 10, "center"))
        ax.annotate(m["name"], (m["weight_gb"], m["score"]), textcoords="offset points",
                    xytext=(dx, dy), fontsize=6.8, color=INK, ha=ha, zorder=4)
    ax.set_xscale("log")
    ax.set_xlim(30, 1600)
    ax.set_ylim(0.30, 1.02)
    seen = []
    for tid in ["A", "B", "C", "D"]:
        if any(m["tier"] == tid for m in scored):
            label = next(m["tier_label"] for m in scored if m["tier"] == tid)
            seen.append(Patch(facecolor=colour[tid], label=f"{tid}: {label}".replace("--", "-")))
    ax.legend(handles=seen, loc="lower right", frameon=False, fontsize=6.8)
    ax.grid(axis="both", color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xlabel("weight memory at served precision (GB, log scale)")
    ax.set_ylabel("mean reward, extension")
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    models = collect(args.root)
    (args.root / "paper/generated").mkdir(parents=True, exist_ok=True)
    (args.root / "paper/figures").mkdir(parents=True, exist_ok=True)
    render_table(models, args.root / "paper/generated/table_hardware_tiers.tex")
    render_figure(models, args.root / "paper/figures/fig_hardware_vs_score.pdf")
    for m in models:
        score = f"{m['score']:.3f}" if m["score"] is not None else "--"
        print(f"  {m['name']:<28} {m['weight_gb']:>6.0f} GB  tier {m['tier']}  hard-8 {score}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
