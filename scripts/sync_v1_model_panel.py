#!/usr/bin/env python3
"""Append live e-INFRA chat models and historically tried OpenRouter models."""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from v1_panel_common import (
    JOBS,
    PANEL,
    PANEL_FIELDS,
    fetch_model_rows,
    provider_token,
)

NON_GENERATIVE_MARKERS = ("embed", "reranker", "whisper")
NON_GENERATIVE_IDS = {"multilingual-e5-large-instruct"}
EINFRA_ROUTING_ALIASES = {
    "agentic",
    "all-proxy-models",
    "auto-llm",
    "auto-llm-heuristic",
    "coder",
    "deepseek",
    "deepseek-thinking",
    "glm",
    "kimi",
    "mini",
    "qwen3.5",
    "thinker",
}


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def display_name(model_id: str) -> str:
    return model_id.rsplit("/", 1)[-1].replace("-", " ").replace(".", ".").title()


def is_einfra_concrete_chat(model_id: str) -> bool:
    lowered = model_id.lower()
    return (
        not any(marker in lowered for marker in NON_GENERATIVE_MARKERS)
        and model_id not in NON_GENERATIVE_IDS
        and model_id not in EINFRA_ROUTING_ALIASES
    )


def openrouter_history() -> set[str]:
    models = set()
    for path in Path(JOBS).glob("*/*/result.json"):
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        model = ((data.get("config") or {}).get("agent") or {}).get("model_name")
        if model and str(model).startswith("openrouter/"):
            models.add(str(model).removeprefix("openrouter/"))
    return models


def existing_rows() -> list[dict[str, str]]:
    if not PANEL.exists():
        return []
    with PANEL.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_panel(rows: list[dict[str, str]]) -> None:
    PANEL.parent.mkdir(exist_ok=True)
    with PANEL.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, PANEL_FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def add_row(
    rows: list[dict[str, str]],
    *,
    provider: str,
    api_model_id: str,
    model_id: str,
    api_base: str,
    provenance: str,
    note: str,
) -> bool:
    if any(row["provider"] == provider and row["api_model_id"] == api_model_id for row in rows):
        return False
    prefix = {"openrouter": "or", "einfra": "ei", "local": "local"}[provider]
    deployment = f"{prefix}-{slug(api_model_id)}"
    if any(row["deployment"] == deployment for row in rows):
        raise RuntimeError(f"deployment slug collision: {deployment}")
    rows.append(
        {
            "deployment": deployment,
            "provider": provider,
            "model_id": model_id,
            "api_model_id": api_model_id,
            "display_name": display_name(api_model_id),
            "api_base": api_base,
            "provenance": provenance,
            "added_at": datetime.now(UTC).isoformat(),
            "notes": note,
        }
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--add-local", action="append", default=[], metavar="HARBOR_MODEL_ID")
    parser.add_argument("--local-api-base", default="")
    args = parser.parse_args()

    rows = existing_rows()
    before = len(rows)
    snapshot: dict[str, object] = {"timestamp": datetime.now(UTC).isoformat(), "providers": {}}

    einfra_models = fetch_model_rows("einfra", provider_token("einfra"))
    einfra_ids = sorted(str(row["id"]) for row in einfra_models)
    snapshot["providers"]["einfra"] = {
        "all_ids": einfra_ids,
        "scheduled_concrete_chat_ids": [model for model in einfra_ids if is_einfra_concrete_chat(model)],
        "excluded_ids": {
            model: "non-generation modality"
            if model in NON_GENERATIVE_IDS
            or any(marker in model.lower() for marker in NON_GENERATIVE_MARKERS)
            else "mutable routing alias"
            for model in einfra_ids
            if not is_einfra_concrete_chat(model)
        },
    }
    for model in einfra_ids:
        if is_einfra_concrete_chat(model):
            add_row(
                rows,
                provider="einfra",
                api_model_id=model,
                model_id=f"openai/{model}",
                api_base="https://llm.ai.e-infra.cz/v1/",
                provenance="live e-INFRA /v1/models",
                note="concrete chat model",
            )

    openrouter_models = fetch_model_rows("openrouter", provider_token("openrouter"))
    openrouter_live = {str(row["id"]) for row in openrouter_models}
    historical = sorted(openrouter_history())
    snapshot["providers"]["openrouter"] = {
        "live_model_count": len(openrouter_live),
        "historically_tried_ids": historical,
        "currently_available": [model for model in historical if model in openrouter_live],
        "currently_unavailable": [model for model in historical if model not in openrouter_live],
    }
    for model in historical:
        availability = "available at panel sync" if model in openrouter_live else "unavailable at panel sync; retain and retry later"
        add_row(
            rows,
            provider="openrouter",
            api_model_id=model,
            model_id=f"openrouter/{model}",
            api_base="",
            provenance="historical local Harbor receipt",
            note=availability,
        )

    for model_id in args.add_local:
        add_row(
            rows,
            provider="local",
            api_model_id=model_id,
            model_id=model_id,
            api_base=args.local_api_base,
            provenance="user-added local deployment",
            note="local runtime; exact quantization and runtime metadata required before publication",
        )

    write_panel(rows)
    snapshot_dir = JOBS / "v1-panel-snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    (snapshot_dir / f"model-discovery-{stamp}.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    )
    print(f"v1 panel: {len(rows)} deployments ({len(rows) - before} appended)")
    print(
        f"e-INFRA concrete chat={len(snapshot['providers']['einfra']['scheduled_concrete_chat_ids'])}; "
        f"OpenRouter historical={len(historical)}; local added={len(args.add_local)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
