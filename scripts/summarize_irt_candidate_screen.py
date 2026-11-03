#!/usr/bin/env python3
"""Summarize one or more Harbor screens of the batch-8 candidate bank."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("jobs", nargs="+", type=Path)
    parser.add_argument("--manifest", type=Path, default=Path("configs/v10_irt_batch8_manifest.tsv"))
    parser.add_argument("--output", type=Path, default=Path("paper/generated/irt_batch8_screen.tsv"))
    args = parser.parse_args()

    with args.manifest.open() as f:
        meta = {r["task"]: r for r in csv.DictReader(f, delimiter="\t")}
    attempts: dict[tuple[str, str], list[float | None]] = defaultdict(list)
    for job in args.jobs:
        for path in sorted(job.glob("*/result.json")):
            data = json.loads(path.read_text())
            task = data.get("task_name")
            if task not in meta:
                continue
            model = data.get("agent_info", {}).get("model_info", {}).get("name", job.name)
            reward = data.get("verifier_result", {}).get("rewards", {}).get("reward")
            attempts[(task, model)].append(None if data.get("exception_info") else reward)

    models = sorted({model for _, model in attempts})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as f:
        fields = ["task", "family", "level", "category"] + [f"{m}:score" for m in models] + [f"{m}:errors" for m in models]
        w = csv.DictWriter(f, fields, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for task, row in meta.items():
            out = {k: row[k] for k in ("task", "family", "level", "category")}
            for model in models:
                vals = attempts.get((task, model), [])
                scored = [x for x in vals if x is not None]
                out[f"{model}:score"] = "" if not scored else f"{sum(scored)}/{len(scored)}"
                out[f"{model}:errors"] = sum(x is None for x in vals)
            w.writerow(out)

    print(f"wrote {args.output}: {len(meta)} tasks, {len(models)} models")
    for model in models:
        vals = [x for (task, m), xs in attempts.items() if m == model for x in xs if x is not None]
        print(f"{model}: {sum(vals):g}/{len(vals)} scored passes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
