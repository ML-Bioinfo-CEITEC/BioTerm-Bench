#!/usr/bin/env python3
"""Item response theory over the task suite: which tasks are good measurements?

A benchmark is a test and its tasks are items, so the psychometric question is
the same one a test designer asks: does each item separate stronger from weaker
respondents, and where on the ability scale does it bite?

We fit a two-parameter logistic model to the binary trial outcomes,

    P(correct | model m, task t) = sigmoid(a_t * (theta_m - b_t))

where ``theta_m`` is model ability, ``b_t`` task difficulty on the same scale,
and ``a_t`` discrimination -- how sharply the task separates models around its
difficulty. An item with a_t near zero (or negative) is not measuring the
ability the rest of the suite measures, whatever its pass rate.

Fitting is joint maximum likelihood with a weak Gaussian prior on all
parameters, which keeps items solved (or failed) by every model from running to
infinite difficulty. With a panel of this size the ability estimates are noisy;
the item parameters, each informed by every model's attempts, are the usable
output. Both are reported with that asymmetry in mind.

Usage:
    python3 scripts/irt_analysis.py
    python3 scripts/irt_analysis.py --min-models 5
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

#: Job globs whose trials enter the fit, paired with the cohort they belong to.
JOB_PATTERNS = [
    ("einfra", "einfra-k4-*"),
    ("einfra", "einfra-core25-k4-*"),
    ("openrouter", "openrouter-addon-hard8-k4-*"),
    ("openrouter", "openrouter-addon-core25-k4-*"),
]

ARCHIVED = (".docker-failed-", ".provider-outage-", ".errored-", ".partial-")


def load_responses(jobs_dir: Path, retired: set[str]) -> tuple[list[str], list[str], np.ndarray, np.ndarray]:
    """Return (models, tasks, successes, attempts) with scored trials only."""
    counts: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for _, pattern in JOB_PATTERNS:
        for job in sorted(jobs_dir.glob(pattern)):
            if not job.is_dir() or any(m in job.name for m in ARCHIVED):
                continue
            result = job / "result.json"
            if not result.exists():
                continue
            model = job.name.split("-k4-", 1)[-1]
            for trial in sorted(job.glob("*/result.json")):
                payload = json.loads(trial.read_text())
                if payload.get("exception_info"):
                    continue  # operational error, not a response
                reward_file = trial.parent / "verifier" / "reward.txt"
                if not reward_file.exists():
                    continue
                try:
                    reward = float(reward_file.read_text().strip())
                except ValueError:
                    continue
                task = trial.parent.name.rsplit("__", 1)[0]
                if task in retired:
                    continue
                cell = counts[(model, task)]
                cell[0] += int(reward >= 0.5)
                cell[1] += 1
    models = sorted({m for m, _ in counts})
    tasks = sorted({t for _, t in counts})
    mi = {m: i for i, m in enumerate(models)}
    ti = {t: i for i, t in enumerate(tasks)}
    successes = np.zeros((len(models), len(tasks)))
    attempts = np.zeros((len(models), len(tasks)))
    for (m, t), (s, n) in counts.items():
        successes[mi[m], ti[t]] = s
        attempts[mi[m], ti[t]] = n
    return models, tasks, successes, attempts


def fit_2pl(successes: np.ndarray, attempts: np.ndarray, prior_sd: float = 2.0):
    """Joint MLE for ability, difficulty, and discrimination."""
    n_models, n_tasks = successes.shape

    def unpack(x):
        theta = x[:n_models]
        b = x[n_models:n_models + n_tasks]
        log_a = x[n_models + n_tasks:]
        return theta, b, np.exp(log_a)

    def negloglik(x):
        theta, b, a = unpack(x)
        z = a[None, :] * (theta[:, None] - b[None, :])
        # log-sum-exp stable Bernoulli log-likelihood
        ll = successes * (-np.logaddexp(0, -z)) + (attempts - successes) * (-np.logaddexp(0, z))
        penalty = (
            np.sum(theta**2) + np.sum(b**2) + np.sum(np.log(a) ** 2)
        ) / (2 * prior_sd**2)
        return -np.sum(ll[attempts > 0]) + penalty

    x0 = np.concatenate([np.zeros(n_models), np.zeros(n_tasks), np.zeros(n_tasks)])
    res = minimize(negloglik, x0, method="L-BFGS-B", options={"maxiter": 20000})
    theta, b, a = unpack(res.x)
    # Identifiability: ability scale is arbitrary, so centre and scale it.
    shift, scale = theta.mean(), theta.std() or 1.0
    theta = (theta - shift) / scale
    b = (b - shift) / scale
    a = a * scale
    return theta, b, a, res


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs-dir", type=Path, default=Path("jobs"))
    parser.add_argument("--retired", type=Path, default=Path("configs/retired_tasks.txt"))
    parser.add_argument("--out", type=Path, default=Path("paper/generated"))
    parser.add_argument("--min-models", type=int, default=3,
                        help="drop tasks attempted by fewer models than this")
    args = parser.parse_args()

    retired = set()
    if args.retired.exists():
        retired = {ln.strip() for ln in args.retired.read_text().splitlines()
                   if ln.strip() and not ln.startswith("#")}

    models, tasks, successes, attempts = load_responses(args.jobs_dir, retired)
    keep = [j for j in range(len(tasks)) if (attempts[:, j] > 0).sum() >= args.min_models]
    tasks = [tasks[j] for j in keep]
    successes, attempts = successes[:, keep], attempts[:, keep]

    theta, b, a, res = fit_2pl(successes, attempts)
    rate = np.divide(successes.sum(0), attempts.sum(0), out=np.zeros(len(tasks)), where=attempts.sum(0) > 0)

    rows = []
    for j, task in enumerate(tasks):
        rows.append({
            "task": task,
            "n_models": int((attempts[:, j] > 0).sum()),
            "n_attempts": int(attempts[:, j].sum()),
            "pass_rate": float(rate[j]),
            "difficulty": float(b[j]),
            "discrimination": float(a[j]),
        })
    rows.sort(key=lambda r: -r["difficulty"])

    abilities = sorted(
        ({"model": m, "ability": float(theta[i])} for i, m in enumerate(models)),
        key=lambda r: -r["ability"],
    )

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "irt_parameters.json").write_text(
        json.dumps({"tasks": rows, "models": abilities,
                    "converged": bool(res.success), "n_models": len(models),
                    "n_tasks": len(tasks)}, indent=2) + "\n")

    # LaTeX table: the ten most informative items and the uninformative tail.
    informative = [r for r in rows if r["pass_rate"] < 1.0]
    ceiling = [r for r in rows if r["pass_rate"] >= 1.0]
    lines = [r"\begin{tabular}{lrrr}", r"\toprule",
             r"Task & Pass rate & Difficulty & Discrimination \\", r"\midrule"]
    for r in informative[:10]:
        lines.append(f"\\texttt{{{r['task'].replace('_', chr(92)+'_')}}} & {r['pass_rate']:.2f} "
                     f"& {r['difficulty']:+.2f} & {r['discrimination']:.2f} \\\\")
    lines.append(r"\midrule")
    lines.append(
        r"\multicolumn{4}{l}{\emph{"
        + f"{len(ceiling)} tasks solved on every scored attempt -- no measurement information"
        + r"}} \\"
    )
    lines += [r"\bottomrule", r"\end{tabular}"]
    (args.out / "table_irt.tex").write_text("\n".join(lines) + "\n")

    print(f"2PL fit over {len(models)} models x {len(tasks)} tasks "
          f"({int(attempts.sum())} scored attempts), converged={res.success}\n")
    print(f"{'task':<34}{'pass':>7}{'diff':>8}{'disc':>8}")
    for r in rows:
        flag = "  <- weak item" if r["discrimination"] < 0.3 else ""
        print(f"  {r['task']:<32}{r['pass_rate']:>7.2f}{r['difficulty']:>8.2f}{r['discrimination']:>8.2f}{flag}")
    print(f"\n{'model':<34}{'ability':>8}")
    for r in abilities:
        print(f"  {r['model']:<32}{r['ability']:>8.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
