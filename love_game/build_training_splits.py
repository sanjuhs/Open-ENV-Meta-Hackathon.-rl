#!/usr/bin/env python3
"""Create deterministic train/validation/test splits for Love Game datasets."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from love_game.common import DATASETS_DIR, read_jsonl, write_jsonl
from love_game.training_text import format_sft_example


DATASET_MAP = {
    "sft": "sft_train.jsonl",
    "dpo": "dpo_train.jsonl",
    "rl": "rl_train.jsonl",
    "rlhf": "rlhf_pairs_train.jsonl",
    "rm_pointwise": "rm_pointwise_train.jsonl",
    "ppo": "ppo_prompts.jsonl",
    "grpo": "grpo_prompts.jsonl",
}


def split_rows(rows: list[dict], val_fraction: float, test_fraction: float, seed: int) -> tuple[list[dict], list[dict], list[dict]]:
    shuffled = list(rows)
    random.Random(seed).shuffle(shuffled)
    total = len(shuffled)
    test_count = int(total * test_fraction)
    val_count = int(total * val_fraction)
    test_rows = shuffled[:test_count]
    val_rows = shuffled[test_count : test_count + val_count]
    train_rows = shuffled[test_count + val_count :]
    return train_rows, val_rows, test_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "love_game" / "splits")
    parser.add_argument("--val-fraction", type=float, default=0.1)
    parser.add_argument("--test-fraction", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {}

    for name, filename in DATASET_MAP.items():
        rows = read_jsonl(DATASETS_DIR / filename)
        if name == "sft":
            rows = [format_sft_example(row) for row in rows]
        train_rows, val_rows, test_rows = split_rows(
            rows,
            val_fraction=args.val_fraction,
            test_fraction=args.test_fraction,
            seed=args.seed,
        )
        for split_name, split_rows_list in (
            ("train", train_rows),
            ("validation", val_rows),
            ("test", test_rows),
        ):
            output_path = args.output_dir / f"{name}_{split_name}.jsonl"
            write_jsonl(output_path, split_rows_list)
        manifest[name] = {
            "train": len(train_rows),
            "validation": len(val_rows),
            "test": len(test_rows),
        }

    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
