#!/usr/bin/env python3
"""Per-task pass rates for the v1.0 hard-candidate search.

A candidate is judged on *discrimination*, not difficulty alone. The screen
deliberately spans the ability range -- a small 27B model, the strongest
e-INFRA model and the weakest -- so the useful signal is the gap between them.
A task the strongest model always solves measures nothing new; a task nobody
solves measures nothing either. This is the lesson of
`bam-splice-junction-support`, admitted on pass rate alone and retired with an
item-total correlation of -0.94.

Usage:
    python3 scripts/hardsearch_status.py [--glob 'hardsearch*-k*'] [--jobs-dir jobs]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

SHORT = {
    "deepseek-v4-flash-thinking": "ds-think",
    "gpt-oss-120b": "oss-120b",
    "qwen38-27b": "qwen38-27b",
}


def model_of(job_name: str) -> str:
    """`hardsearch-k3-gpt-oss-120b` and `hardsearch2-k3-gpt-oss-120b` are the
    same model screened on different task sets."""
    parts = job_name.split("-")
    for i, p in enumerate(parts):
        if p.startswith("k") and p[1:].isdigit():
            return "-".join(parts[i + 1:])
    return job_name


def load(jobs_dir: Path, pattern: str) -> dict[str, dict[str, list[float | None]]]:
    per: dict[str, dict[str, list[float | None]]] = defaultdict(lambda: defaultdict(list))
    for result in sorted(jobs_dir.glob(f"{pattern}/*/result.json")):
        model = model_of(result.parent.parent.name)
        data = json.loads(result.read_text())
        if data.get("exception_info"):
            per[data["task_name"]][model].append(None)      # error, not a score
            continue
        rewards = (data.get("verifier_result") or {}).get("rewards") or {}
        per[data["task_name"]][model].append(rewards.get("reward"))
    return per


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs-dir", type=Path, default=Path("jobs"))
    parser.add_argument("--glob", default="hardsearch*-k*")
    parser.add_argument("--only-new", action="store_true",
                        help="restrict to the v1.0 candidate task lists")
    args = parser.parse_args()

    per = load(args.jobs_dir, args.glob)
    if args.only_new:
        keep = set()
        for name in ("configs/v10_candidates.txt", "configs/v10_round2_tasks.txt"):
            p = Path(name)
            if p.exists():
                keep |= {x.strip() for x in p.read_text().split() if x.strip()}
        per = {t: v for t, v in per.items() if t in keep}
    if not per:
        print("no trials yet")
        return 0

    models = sorted({m for t in per.values() for m in t})
    short = {m: SHORT.get(m, m)[:12] for m in models}
    width = max(len(t) for t in per) + 2

    head = f"{'task':<{width}}" + "".join(f"{short[m]:>13}" for m in models) + f"{'pooled':>9}"
    print(head)
    print("-" * len(head))
    solved_all, solved_none, discriminating = [], [], []
    for task in sorted(per):
        line = f"{task:<{width}}"
        got = []
        for m in models:
            vals = [v for v in per[task].get(m, []) if v is not None]
            n_err = sum(1 for v in per[task].get(m, []) if v is None)
            if not vals:
                line += f"{('err' if n_err else '-'):>13}"
                continue
            got.extend(vals)
            line += f"{f'{sum(1 for v in vals if v >= 1.0)}/{len(vals)}':>13}"
        n_ok = sum(1 for v in got if v >= 1.0)
        pooled = f"{n_ok}/{len(got)}" if got else "-"
        print(line + f"{pooled:>9}")
        if got:
            (solved_all if n_ok == len(got) else
             solved_none if n_ok == 0 else discriminating).append(task)

    print()
    print(f"solved by everyone, every attempt : {len(solved_all)}")
    print(f"solved by nobody                  : {len(solved_none)}")
    print(f"discriminating (someone fails)    : {len(discriminating)}")
    for t in discriminating:
        print(f"    {t}")
    done = sum(len(v) for t in per.values() for v in t.values())
    print(f"\n{done} trials scored across {len(models)} models and {len(per)} tasks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
