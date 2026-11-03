#!/usr/bin/env python3
"""Why did the failed trials on the new candidate tasks fail?

The graders print a one-line diagnosis to stdout ("line 7 column x: actual=..
gold=.."), so the failures can be classified without reading trajectories.
Six batches of guessing at what makes a task hard produced one frontier
failure; this reads the evidence instead.

Usage:
    python3 scripts/failure_reasons.py [--jobs-dir jobs]
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


def classify(text: str) -> str:
    t = text.strip()
    if not t:
        return "no grader output"
    if "missing " in t:
        return "no output file produced"
    if "header must be" in t:
        return "wrong header"
    if "data rows" in t:
        return "wrong number of rows"
    if "tab-separated columns" in t or "columns, got" in t:
        return "wrong column count"
    if "is not numeric" in t:
        return "non-numeric where a number was required"
    if re.search(r"column \w+: actual=", t):
        return "wrong value in a cell"
    if "SyntaxError" in t or "Traceback" in t:
        return "GRADER CRASHED"
    return "other"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs-dir", type=Path, default=Path("jobs"))
    args = ap.parse_args()

    reasons: Counter[str] = Counter()
    per_model: dict[str, Counter] = {}
    examples: dict[str, str] = {}
    n_pass = 0
    for result in sorted(args.jobs_dir.glob("hardsearch*-k*/*/result.json")):
        job = result.parent.parent.name
        parts = job.split("-")
        model = "-".join(parts[parts.index(next(p for p in parts
                                                if p.startswith("k") and p[1:].isdigit())) + 1:])
        data = json.loads(result.read_text())
        reward = ((data.get("verifier_result") or {}).get("rewards") or {}).get("reward")
        if reward is not None and reward >= 1.0:
            n_pass += 1
            continue
        out = result.parent / "verifier" / "test-stdout.txt"
        text = out.read_text() if out.exists() else ""
        line = next((x for x in text.splitlines() if x.startswith("FAIL:")), text[-200:])
        why = classify(text)
        reasons[why] += 1
        per_model.setdefault(model, Counter())[why] += 1
        examples.setdefault(f"{data['task_name']} | {why}", line.strip()[:150])

    total = sum(reasons.values())
    print(f"{n_pass} passed, {total} failed\n")
    print("why the failures failed")
    for why, n in reasons.most_common():
        print(f"  {n:>3}  {n / total:>5.0%}  {why}")
    print("\nby model")
    for model, c in sorted(per_model.items()):
        print(f"  {model}: " + ", ".join(f"{w} x{n}" for w, n in c.most_common()))
    print("\nexamples")
    for k, v in sorted(examples.items())[:14]:
        print(f"  {k}\n      {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
