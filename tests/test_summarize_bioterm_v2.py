from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.summarize_bioterm_v2 import (
    ModelSummary,
    analyze,
    bootstrap_clustered_reward_interval,
    classify_status,
    clopper_pearson_interval,
    read_trials,
    render_headline_table,
)


def write_task(tasks_dir: Path, name: str, category: str) -> None:
    task_dir = tasks_dir / name
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "task.toml").write_text(
        "\n".join(
            [
                'version = "1.0"',
                "[metadata]",
                f'category = "{category}"',
                'difficulty = "medium"',
            ]
        )
        + "\n"
    )


def write_trial(
    job_dir: Path,
    task: str,
    suffix: str,
    reward: float | None,
    *,
    tokens: int = 10,
    rollouts: int = 1,
    exception_type: str | None = None,
    exception_message: str | None = None,
    model_id: str = "openrouter/openai/gpt-oss-20b",
) -> None:
    trial_dir = job_dir / f"{task}__{suffix}"
    trial_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "task_name": task,
        "trial_name": f"{task}__{suffix}",
        "started_at": f"2026-05-01T10:00:{suffix.zfill(2)}Z",
        "config": {"agent": {"model_name": model_id}},
        "agent_result": {
            "cost_usd": 0.1 if tokens else 0.0,
            "n_input_tokens": tokens,
            "n_output_tokens": tokens,
            "n_cache_tokens": 0,
            "rollout_details": [{}] * rollouts,
            "metadata": {"n_episodes": 1},
        },
        "verifier_result": None if reward is None else {"rewards": {"reward": reward}},
        "exception_info": None
        if exception_type is None
        else {"exception_type": exception_type, "exception_message": exception_message or exception_type},
    }
    (trial_dir / "result.json").write_text(json.dumps(payload))


def write_job(job_dir: Path, expected_trials: int) -> None:
    (job_dir / "result.json").write_text(
        json.dumps(
            {
                "started_at": "2026-05-01T10:00:00Z",
                "finished_at": "2026-05-01T10:30:00Z",
                "n_total_trials": expected_trials,
            }
        )
    )


class SummarizeBioTermV2Tests(unittest.TestCase):
    def test_clustered_bootstrap_retains_scored_attempts(self) -> None:
        lo, hi = bootstrap_clustered_reward_interval([[1.0, 1.0], [0.0]], seed=7)
        self.assertLessEqual(lo, 0.0)
        self.assertGreaterEqual(hi, 1.0)

    def test_clopper_pearson_edges(self) -> None:
        lo, hi = clopper_pearson_interval(0, 25)
        self.assertEqual(lo, 0.0)
        self.assertGreater(hi, 0.0)
        self.assertLess(hi, 0.2)
        lo2, hi2 = clopper_pearson_interval(25, 25)
        self.assertGreater(lo2, 0.8)
        self.assertLess(lo2, 1.0)
        self.assertEqual(hi2, 1.0)

    def test_all_timeout_job_is_excluded_high_error_rate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            job_dir = tmp_path / "jobs" / "broken"
            job_dir.mkdir(parents=True)
            write_job(job_dir, expected_trials=4)
            for idx in range(4):
                write_trial(
                    job_dir,
                    "task-a",
                    str(idx),
                    0.0,
                    tokens=100,
                    rollouts=0,
                    exception_type="AgentTimeoutError",
                    exception_message="Agent execution timed out after 900.0 seconds",
                )
            status, reason = classify_status(
                result=json.loads((job_dir / "result.json").read_text()),
                trials=read_trials(job_dir),
                expected_trials=4,
                attempts_per_task=4,
                max_error_rate=0.20,
            )
            self.assertEqual(status, "excluded")
            self.assertEqual(reason, "protocol_failure_high_error_rate")

    def test_mixed_scored_and_error_attempts_keep_scored_denominators(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            tasks_dir = tmp_path / "tasks"
            for name, category in [
                ("task-a", "alignment"),
                ("task-b", "variant"),
                ("task-c", "qc"),
                ("task-d", "search"),
                ("task-e", "rnaseq"),
            ]:
                write_task(tasks_dir, name, category)

            jobs_dir = tmp_path / "jobs"
            job_dir = jobs_dir / "full25-k4-open-gpt-oss-20b"
            job_dir.mkdir(parents=True)
            write_job(job_dir, expected_trials=10)

            write_trial(job_dir, "task-a", "01", None, tokens=0, rollouts=0)  # error first attempt
            write_trial(job_dir, "task-a", "02", 1.0)
            write_trial(job_dir, "task-b", "03", 0.0)
            write_trial(job_dir, "task-b", "04", 1.0)
            write_trial(job_dir, "task-c", "05", 1.0)
            write_trial(job_dir, "task-c", "06", None, tokens=0, rollouts=0)  # error second attempt
            write_trial(job_dir, "task-d", "07", 0.0)
            write_trial(job_dir, "task-d", "08", 0.0)
            write_trial(job_dir, "task-e", "09", 1.0)
            write_trial(job_dir, "task-e", "10", 1.0)

            out_dir = tmp_path / "paper" / "generated"
            summary = analyze(
                jobs_dir=jobs_dir,
                tasks_dir=tasks_dir,
                pattern="full25-k4-open-*",
                cohort_name="toy",
                expected_trials=10,
                attempts_per_task=2,
                max_error_rate=0.20,
                out_dir=out_dir,
                provider="openrouter",
                score_scope="hard-subset",
            )

            self.assertEqual(summary["included_models"], ["full25-k4-open-gpt-oss-20b"])
            models_csv = (out_dir / "toy_models.csv").read_text()
            self.assertIn(",0.2,", models_csv)  # error_rate
            self.assertIn("pass_at_1_scored_denominator", models_csv.splitlines()[0])
            self.assertIn("pass_at_k_scored_denominator", models_csv.splitlines()[0])
            self.assertIn("provider", models_csv.splitlines()[0])
            self.assertIn("score_scope", models_csv.splitlines()[0])
            self.assertIn("openrouter,2026-05-01,hard-subset", models_csv)
            self.assertIn(",2,4,0.5,", models_csv)  # pass@1 count / scored denom / rate
            self.assertIn(",4,5,0.8,", models_csv)  # pass@k count / scored denom / rate
            self.assertIn(",0.625,", models_csv)  # mean reward over scored trials only: 5/8
            headline = (out_dir / "table_headline.tex").read_text()
            self.assertIn("2/4", headline)
            self.assertIn("4/5", headline)

    def test_analysis_rejects_mixed_provider_glob(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            tasks_dir = tmp_path / "tasks"
            write_task(tasks_dir, "task-a", "alignment")
            jobs_dir = tmp_path / "jobs"
            for job_name, model_id in (
                ("full25-k4-open-model", "openrouter/example/model"),
                ("einfra-k4-model", "openai/model"),
            ):
                job_dir = jobs_dir / job_name
                job_dir.mkdir(parents=True)
                write_job(job_dir, expected_trials=1)
                write_trial(job_dir, "task-a", "01", 1.0, model_id=model_id)
            with self.assertRaisesRegex(RuntimeError, "mixes provider cohorts"):
                analyze(
                    jobs_dir=jobs_dir,
                    tasks_dir=tasks_dir,
                    pattern="*",
                    cohort_name="mixed",
                    expected_trials=1,
                    attempts_per_task=1,
                    max_error_rate=0.20,
                    out_dir=tmp_path / "out",
                    provider="unknown",
                )


if __name__ == "__main__":
    unittest.main()


class HeadlineCostColumnTest(unittest.TestCase):
    """Cost is only printed for providers that actually bill per token.

    litellm reports a ``cost_usd`` even for models it cannot price -- it logs
    "isn't mapped yet" and falls back -- so on the university-hosted e-INFRA
    endpoint the summed figure is an artifact of an inapplicable price map.
    Rendering it as dollars would put a fabricated number in the paper.
    """

    def _row(self) -> ModelSummary:
        fields = {name: 0 for name in ModelSummary.__dataclass_fields__}
        fields.update(
            model_label="Gemma4",
            pass_at_1_count=5,
            pass_at_1_scored_denominator=8,
            pass_at_k_count=7,
            pass_at_k_scored_denominator=8,
            all_scored_pass_count=5,
            mixed_count=2,
            scored_task_count=8,
            mean_reward=0.688,
            total_cost_usd=0.3228,
        )
        return ModelSummary(**fields)

    def _render(self, provider: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "table.tex"
            render_headline_table(path, [self._row()], 4, provider)
            return path.read_text()

    def test_einfra_table_omits_cost(self) -> None:
        rendered = self._render("einfra")
        self.assertNotIn("Cost (USD)", rendered)
        self.assertNotIn("0.32", rendered)
        self.assertIn("{lrrrrr}", rendered)
        self.assertIn("0.688", rendered)

    def test_openrouter_table_keeps_cost(self) -> None:
        rendered = self._render("openrouter")
        self.assertIn("Cost (USD)", rendered)
        self.assertIn("0.32", rendered)
        self.assertIn("{lrrrrrr}", rendered)
