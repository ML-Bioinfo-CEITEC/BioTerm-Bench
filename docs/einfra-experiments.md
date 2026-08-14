# Running BioTerm-Bench on e-INFRA

The e-INFRA endpoint is an OpenAI-compatible shared research service. Its
operators require benchmark traffic to be coordinated in advance. Queueing on
the shared deployment makes wall time unsuitable as a model-speed comparison.
Read the [official service guidance](https://docs.cerit.io/en/docs/ai-as-a-service/chat-ai)
before running this workflow.

## Credentials

Generate an API key through the e-INFRA WebUI and export it only in the shell
that starts the run:

```bash
export EINFRA_AI_TOKEN='...'
```

The runner maps this value to the OpenAI-compatible client process without
writing it to command lines, manifests, snapshots, logs, or Harbor artifacts.

## Validate and run

```bash
# Resolve all exact IDs without starting Harbor jobs.
python scripts/run_einfra_panel.py --validate-only

# Snapshot provider metadata and print the complete smoke/full command plan.
# This intentionally fails before a full run until task selection is complete.
python scripts/run_einfra_panel.py --dry-run

# Smoke-test tool use, then execute the retained v2 tasks at four attempts.
python scripts/run_einfra_panel.py --smoke
python scripts/run_einfra_panel.py  # requires matching notes/v2_task_selection.json
```

The three-task smoke gate inspects the stored Terminus trajectory, not just the
Harbor exit code. Three trials without a parsed terminal tool call, or with an
explicit tool/protocol/parser exception, mark that exact deployment as
incompatible and prevent a full sweep.

The exact command-line interface is documented by
`python scripts/run_einfra_panel.py --help`. Runs are sequential by model,
begin at one concurrent trial, and never exceed two. Model aliases are not used
as silent fallbacks.

## Monitor and resume

The monitor appends a machine-readable checkpoint every 15 minutes. The state
records completed and expected trials, recent errors, last progress time,
live public service state and queue counts, concurrency, and an ETA. An interrupted Harbor job is resumed
from its existing directory:

```bash
harbor job resume --job-path jobs/<job-name>
```

On throttling, or when a public queue persists without progress for 15 minutes,
the runner stops new submissions, cools down for 15, 30, then 60 minutes, and
remains at concurrency one. Authentication failures stop the panel without
retrying. Exact models unavailable for one hour are recorded and revisited once
after the remaining panel. Exhausted retries and a failed revisit are explicit
terminal status rows; a model cannot silently disappear from the panel receipt.

## Reproducibility

Every run snapshots the authenticated `/v1/models` response, the public status
metadata, manifest, run timestamp, and Harbor version. Exact deployments are
short-lived, so retain all raw responses and trial artifacts needed to audit a
reported score.
