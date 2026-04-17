#!/usr/bin/env python3
"""Count tokenizer footprint for Love Game datasets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from love_game.common import DATASETS_DIR, read_jsonl
from love_game.training_text import format_sft_example


DEFAULT_MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"


def count_field_tokens(tokenizer, rows: list[dict], field: str) -> dict:
    total = 0
    max_len = 0
    for row in rows:
        value = row[field]
        tokens = len(tokenizer(value, add_special_tokens=False)["input_ids"])
        total += tokens
        max_len = max(max_len, tokens)
    return {
        "field": field,
        "rows": len(rows),
        "total_tokens": total,
        "avg_tokens": round(total / max(1, len(rows)), 2),
        "max_tokens": max_len,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--dataset-dir", type=Path, default=DATASETS_DIR)
    args = parser.parse_args()

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    files = [
        "sft_train.jsonl",
        "dpo_train.jsonl",
        "rl_train.jsonl",
        "rlhf_pairs_train.jsonl",
        "rm_pointwise_train.jsonl",
        "ppo_prompts.jsonl",
        "grpo_prompts.jsonl",
    ]
    report = []
    for filename in files:
        path = args.dataset_dir / filename
        if not path.exists():
            continue
        rows = read_jsonl(path)
        total = 0
        max_len = 0
        for row in rows:
            text = json.dumps(row, ensure_ascii=False)
            tokens = len(tokenizer(text, add_special_tokens=False)["input_ids"])
            total += tokens
            max_len = max(max_len, tokens)
        report.append(
            {
                "file": filename,
                "rows": len(rows),
                "total_tokens": total,
                "avg_tokens": round(total / max(1, len(rows)), 2),
                "max_tokens": max_len,
            }
        )

    sft_rows = [format_sft_example(row) for row in read_jsonl(args.dataset_dir / "sft_train.jsonl")]
    sft_breakdown = [
        count_field_tokens(tokenizer, sft_rows, "prompt"),
        count_field_tokens(tokenizer, sft_rows, "completion"),
        count_field_tokens(tokenizer, sft_rows, "text"),
    ]
    payload = {
        "model": args.model,
        "datasets": report,
        "sft_breakdown": sft_breakdown,
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
