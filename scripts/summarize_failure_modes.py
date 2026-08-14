#!/usr/bin/env python3
"""Classify scored benchmark failures by how the artifact failed.

A binary verifier records *that* a task failed, not *how*. The practical cost
of the two failure families is very different: an absent or malformed artifact
announces itself, while a well-formed but incorrect artifact passes structural
checks and propagates silently into whatever consumes it.

Failures are read from the verifier's own stdout (``verifier/test-stdout.txt``),
whose graders emit a ``FAIL: <reason>`` line (the first is used), and bucketed as:

``missing``      no output file was produced at all;
``malformed``    a file exists but violates the declared structure
                 (unparseable JSON, wrong column count, bad row shape);
``wrong_value``  the artifact is structurally valid and its contents disagree
                 with the gold answer -- the quiet, expensive case;
``unclassified`` a FAIL reason not matched by the patterns above.

Trials carrying an ``exception_info`` payload are operational errors, not
scored failures, and are excluded -- the same rule the headline tables use.

Usage:
    python3 scripts/summarize_failure_modes.py jobs/full25-k4-open-*
    python3 scripts/summarize_failure_modes.py --csv out.csv jobs/einfra-k4-*
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

MISSING = re.compile(
    r"\bmissing\b|\bno such file\b|\bdoes not exist\b|output is empty|\bis empty\b",
    re.IGNORECASE,
)
MALFORMED = re.compile(
    r"not parseable|not valid json|invalid json|expected \d+ tab-columns|"
    r"expected \d+ columns|not exactly \d+ tab-columns|malformed|could not parse|unreadable|"
    r"expecting ['\"]?,|delimiter|header must be|non-empty lines|"
    r"must be int|must be float|is not numeric|got str|failed to open|"
    r"not integer|bad row",
    re.IGNORECASE,
)
WRONG_VALUE = re.compile(
    r"actual=|mismatch|expected=|gold=|differs|!=|does not match|" r"wrong value|value error",
    re.IGNORECASE,
)


def classify(reason: str) -> str:
    """Bucket one FAIL reason.

    Order matters: a missing file also mentions a path, and a malformed file
    often also reports a value, so the most specific structural signal wins
    before falling through to a content mismatch.
    """
    if MISSING.search(reason):
        return "missing"
    if MALFORMED.search(reason):
        return "malformed"
    if WRONG_VALUE.search(reason):
        return "wrong_value"
    return "unclassified"


def first_fail_reason(trial_dir: Path) -> str | None:
    stdout_path = trial_dir / "verifier" / "test-stdout.txt"
    if not stdout_path.exists():
        return None
    for line in stdout_path.read_text(errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("FAIL:"):
            return stripped[len("FAIL:") :].strip()
    return None


def trial_reward(trial_dir: Path) -> float | None:
    reward_path = trial_dir / "verifier" / "reward.txt"
    if not reward_path.exists():
        return None
    try:
        return float(reward_path.read_text().strip())
    except ValueError:
        return None


def has_exception(trial_dir: Path) -> bool:
    result_path = trial_dir / "result.json"
    if not result_path.exists():
        return False
    try:
        payload = json.loads(result_path.read_text())
    except json.JSONDecodeError:
        return False
    return bool(payload.get("exception_info"))


def summarize(job_dirs: list[Path]) -> tuple[Counter[str], list[dict[str, str]]]:
    counts: Counter[str] = Counter()
    rows: list[dict[str, str]] = []
    for job_dir in job_dirs:
        if not job_dir.is_dir():
            continue
        for trial_dir in sorted(p for p in job_dir.iterdir() if p.is_dir()):
            if has_exception(trial_dir):
                continue
            if trial_reward(trial_dir) != 0.0:
                continue
            reason = first_fail_reason(trial_dir)
            if reason is None:
                continue
            bucket = classify(reason)
            counts[bucket] += 1
            rows.append(
                {
                    "job": job_dir.name,
                    "trial": trial_dir.name,
                    "task": trial_dir.name.rsplit("__", 1)[0],
                    "bucket": bucket,
                    "reason": reason,
                }
            )
    return counts, rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("job_dirs", nargs="+", type=Path)
    parser.add_argument("--csv", type=Path, help="write per-trial classifications here")
    args = parser.parse_args()

    counts, rows = summarize(args.job_dirs)
    total = sum(counts.values())
    if not total:
        print("no scored failures with verifier output found", file=sys.stderr)
        return 1

    print(f"scored failures classified: {total}")
    for bucket in ("missing", "malformed", "wrong_value", "unclassified"):
        n = counts[bucket]
        print(f"  {bucket:<14} {n:>5}  {n / total:6.1%}")
    quiet = counts["wrong_value"]
    print(f"\nstructurally valid but incorrect: {quiet}/{total} = {quiet / total:.1%}")

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=["job", "trial", "task", "bucket", "reason"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
