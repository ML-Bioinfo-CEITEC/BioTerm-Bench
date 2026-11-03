#!/usr/bin/env python3
"""Report per-model progress for the incremental BioTerm-Bench v1 campaign."""

from __future__ import annotations

import argparse
from collections import Counter

from v1_panel_common import JOBS, PAUSE_MARKER, job_counts, job_name, load_panel


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-attempts", type=int, choices=range(1, 6), default=None)
    parser.add_argument("--provider", choices=("openrouter", "einfra", "local"), default=None)
    args = parser.parse_args()
    target_file = JOBS / "v1-target-attempts"
    target = args.target_attempts or (int(target_file.read_text()) if target_file.exists() else 1)
    rows = load_panel()
    if args.provider:
        rows = [row for row in rows if row["provider"] == args.provider]
    totals = Counter()
    print(f"state={'PAUSED' if PAUSE_MARKER.exists() else 'UNPAUSED'} target_k={target}")
    for row in rows:
        completed = scored = errors = passed = 0
        for attempt in range(1, target + 1):
            path = JOBS / job_name(row["deployment"], attempt)
            wave_scored, wave_errors, wave_passed = job_counts(path)
            scored += wave_scored
            errors += wave_errors
            passed += wave_passed
            if wave_scored == 50 and wave_errors == 0:
                completed += 1
        totals["models"] += 1
        totals["completed_waves"] += completed
        totals["scored"] += scored
        totals["errors"] += errors
        rate = passed / scored if scored else 0.0
        print(
            f"{row['deployment']:<58} {row['provider']:<10} "
            f"waves={completed}/{target} scored={scored}/{50 * target} errors={errors} pass={rate:.3f}"
        )
    print(
        f"TOTAL models={totals['models']} waves={totals['completed_waves']}/{totals['models'] * target} "
        f"scored={totals['scored']}/{totals['models'] * target * 50} errors={totals['errors']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
