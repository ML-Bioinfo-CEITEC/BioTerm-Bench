#!/usr/bin/env python3
"""Keep-or-cut recommendation for every v1.0 candidate task.

Selection is on *discrimination*, not difficulty. The screening panel spans the
ability range on purpose -- a 27B model, the strongest e-INFRA model and the
weakest -- so the signal is which models a task separates. A task everyone
solves on every attempt measures nothing, however intricate it was to write;
that is the lesson of `bam-splice-junction-support`, admitted on pass rate
alone and retired at an item-total correlation of -0.94.

With three models the classical item statistics are far too noisy to fit, so
this reports the raw per-model pass rates and a transparent rule rather than a
2PL fit that would imply precision it does not have.

Usage:
    python3 scripts/candidate_recommendation.py
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

#: Screening panel ordered weakest to strongest, by their measured mean reward
#: on the existing extension (0.423 and 1.000 respectively).
LADDER = ["gpt-oss-120b", "qwen38-27b", "deepseek-v4-flash-thinking"]


def model_of(job: str) -> str:
    parts = job.split("-")
    for i, p in enumerate(parts):
        if p.startswith("k") and p[1:].isdigit():
            return "-".join(parts[i + 1:])
    return job


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs-dir", type=Path, default=Path("jobs"))
    args = ap.parse_args()

    per: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in sorted(args.jobs_dir.glob("hardsearch*-k*/*/result.json")):
        d = json.loads(r.read_text())
        reward = ((d.get("verifier_result") or {}).get("rewards") or {}).get("reward")
        if d.get("exception_info") or reward is None:
            continue
        per[d["task_name"]][model_of(r.parent.parent.name)].append(float(reward))

    keep, cut, review = [], [], []
    print(f"{'task':<38}{'weak':>7}{'mid':>7}{'strong':>8}  recommendation")
    print("-" * 78)
    for task in sorted(per):
        cells = []
        for m in LADDER:
            v = per[task].get(m, [])
            cells.append(f"{sum(1 for x in v if x >= 1.0)}/{len(v)}" if v else "-")
        got = [x for v in per[task].values() for x in v]
        n_ok = sum(1 for x in got if x >= 1.0)
        strong = per[task].get("deepseek-v4-flash-thinking", [])
        strong_ok = all(x >= 1.0 for x in strong) if strong else None

        if n_ok == len(got):
            verdict, bucket = "cut -- nobody fails it", cut
        elif n_ok == 0:
            verdict, bucket = "review -- nobody passes; check the task", review
        elif strong_ok is False:
            verdict, bucket = "KEEP -- separates at the top", keep
        else:
            verdict, bucket = "keep -- separates at the bottom", keep
        bucket.append(task)
        print(f"{task:<38}" + "".join(f"{c:>7}" if i < 2 else f"{c:>8}"
                                      for i, c in enumerate(cells)) + f"  {verdict}")

    print()
    print(f"keep   {len(keep):>3}")
    print(f"cut    {len(cut):>3}")
    print(f"review {len(review):>3}")
    print("\nColumns are the screening ladder: gpt-oss-120b (weakest, 0.423 on the")
    print("existing extension), qwen3.8-27b, deepseek-v4-flash-thinking (1.000).")
    print("A dash means that model has not screened the task.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
