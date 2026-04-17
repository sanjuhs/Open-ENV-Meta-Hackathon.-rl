"""Shared helpers for Love Game datasets and local tools."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOVE_GAME_DIR = ROOT / "love_game"
DATASETS_DIR = LOVE_GAME_DIR / "datasets"
MODE_TO_FILE = {
    "sft": "sft_train.jsonl",
    "dpo": "dpo_train.jsonl",
    "rl": "rl_train.jsonl",
    "reward_model": "reward_model_train.jsonl",
    "ppo": "ppo_prompts.jsonl",
    "grpo": "grpo_prompts.jsonl",
    "rlhf": "rlhf_pairs_train.jsonl",
    "rm_pointwise": "rm_pointwise_train.jsonl",
}


def compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def list_dataset_files() -> list[Path]:
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(DATASETS_DIR.glob("*.jsonl"))


def normalize_json_value(value: Any) -> Any:
    if isinstance(value, str):
        return compact_text(value)
    if isinstance(value, list):
        return [normalize_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_json_value(value[key]) for key in sorted(value)}
    return value


def row_signature(row: dict) -> str:
    normalized = normalize_json_value(row)
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True)


def dedupe_rows(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for row in rows:
        sig = row_signature(row)
        if sig in seen:
            continue
        seen.add(sig)
        deduped.append(row)
    return deduped


def load_env_key(env_name: str) -> str:
    value = os.getenv(env_name, "")
    if value:
        return value
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{env_name}="):
                parsed = line.split("=", 1)[1].strip().strip('"')
                if parsed:
                    return parsed
    raise RuntimeError(f"Missing {env_name} in environment and .env")
