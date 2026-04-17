#!/usr/bin/env python3
"""Train a PPO-compatible reward model for Love Game using TRL RewardTrainer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from datasets import load_dataset
from transformers import AutoTokenizer
from trl import RewardConfig, RewardTrainer

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-dataset", type=Path, required=True)
    parser.add_argument("--eval-dataset", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-length", type=int, default=768)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--per-device-train-batch-size", type=int, default=8)
    parser.add_argument("--per-device-eval-batch-size", type=int, default=8)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=1)
    parser.add_argument("--num-train-epochs", type=float, default=2.0)
    parser.add_argument("--logging-steps", type=int, default=10)
    parser.add_argument("--eval-steps", type=int, default=25)
    parser.add_argument("--save-steps", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def normalize_row(row: dict) -> dict:
    return {
        "prompt": row["prompt"],
        "chosen": row["preferred_response"],
        "rejected": row["dispreferred_response"],
    }


def main() -> None:
    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    train_dataset = load_dataset("json", data_files=str(args.train_dataset), split="train").map(normalize_row)
    eval_dataset = load_dataset("json", data_files=str(args.eval_dataset), split="train").map(normalize_row)

    trainer = RewardTrainer(
        model=args.model,
        processing_class=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        args=RewardConfig(
            output_dir=str(args.output_dir),
            learning_rate=args.learning_rate,
            per_device_train_batch_size=args.per_device_train_batch_size,
            per_device_eval_batch_size=args.per_device_eval_batch_size,
            gradient_accumulation_steps=args.gradient_accumulation_steps,
            num_train_epochs=args.num_train_epochs,
            logging_steps=args.logging_steps,
            eval_steps=args.eval_steps,
            save_steps=args.save_steps,
            eval_strategy="steps",
            save_strategy="steps",
            save_total_limit=2,
            bf16=True,
            report_to="none",
            seed=args.seed,
            max_length=args.max_length,
        ),
    )

    trainer.train()
    trainer.save_model()
    tokenizer.save_pretrained(args.output_dir)

    final_metrics = trainer.evaluate()
    (args.output_dir / "final_metrics.json").write_text(
        json.dumps(final_metrics, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(final_metrics, indent=2))


if __name__ == "__main__":
    main()
