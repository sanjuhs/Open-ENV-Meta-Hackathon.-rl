#!/usr/bin/env python3
"""Export a snapshot of Love Game datasets with a dataset card for Hugging Face upload."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from love_game.common import DATASETS_DIR, list_dataset_files, read_jsonl


DEFAULT_MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repo-id", default="sanjuhs/adt-personality-dataset")
    parser.add_argument("--tokenizer-model", default=DEFAULT_MODEL)
    parser.add_argument("--milestone", default="manual")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer_model, trust_remote_code=True)

    summary: dict[str, dict[str, float | int | str]] = {}
    combined_tokens = 0
    combined_rows = 0
    copied_files: list[str] = []

    for path in list_dataset_files():
        rows = read_jsonl(path)
        total_tokens = 0
        max_tokens = 0
        for row in rows:
            text = json.dumps(row, ensure_ascii=False)
            token_count = len(tokenizer(text, add_special_tokens=False)["input_ids"])
            total_tokens += token_count
            max_tokens = max(max_tokens, token_count)
        combined_tokens += total_tokens
        combined_rows += len(rows)
        summary[path.name] = {
            "rows": len(rows),
            "total_tokens": total_tokens,
            "avg_tokens": round(total_tokens / max(1, len(rows)), 2),
            "max_tokens": max_tokens,
        }
        shutil.copy2(path, args.output_dir / path.name)
        copied_files.append(path.name)

    manifest = {
        "repo_id": args.repo_id,
        "milestone": args.milestone,
        "combined_rows": combined_rows,
        "combined_tokens": combined_tokens,
        "datasets": summary,
        "copied_files": copied_files,
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    readme = f"""# ADT Personality Dataset

Synthetic conversational personality dataset for the Love Game experiments.

## Snapshot

- Milestone: `{args.milestone}`
- Combined rows: `{combined_rows}`
- Combined tokens: `{combined_tokens}`
- Tokenizer used for accounting: `{args.tokenizer_model}`

## Files

{chr(10).join(f"- `{name}`: {meta['rows']} rows, {meta['total_tokens']} tokens" for name, meta in summary.items())}

## Notes

- This snapshot is synthetic.
- It contains SFT, preference, reward-model, PPO-prompt, and GRPO-prompt style datasets.
- Multi-turn context is preserved where available.
"""
    (args.output_dir / "README.md").write_text(readme, encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
