#!/usr/bin/env python3
"""Train a neural reward model for Love Game using a tiny transformer."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_MODEL = "distilroberta-base"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-dataset", type=Path, required=True)
    parser.add_argument("--eval-dataset", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--per-device-train-batch-size", type=int, default=16)
    parser.add_argument("--per-device-eval-batch-size", type=int, default=16)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=1)
    parser.add_argument("--num-train-epochs", type=float, default=3.0)
    parser.add_argument("--logging-steps", type=int, default=10)
    parser.add_argument("--eval-steps", type=int, default=25)
    parser.add_argument("--save-steps", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def normalize_pointwise_row(row: dict) -> dict:
    return {
        "text": f"{row['prompt']}\n\nResponse:\n{row['response']}",
        "label": int(row["label"]),
    }


def tokenize_row(row: dict, tokenizer, max_length: int) -> dict:
    encoded = tokenizer(
        row["text"],
        truncation=True,
        max_length=max_length,
        padding=False,
    )
    encoded["labels"] = row["label"]
    return encoded


def compute_metrics(eval_pred) -> dict[str, float]:
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    accuracy = float((preds == labels).mean())
    return {"accuracy": accuracy}


def main() -> None:
    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    train_dataset = load_dataset("json", data_files=str(args.train_dataset), split="train").map(normalize_pointwise_row)
    eval_dataset = load_dataset("json", data_files=str(args.eval_dataset), split="train").map(normalize_pointwise_row)

    train_dataset = train_dataset.map(
        lambda row: tokenize_row(row, tokenizer, args.max_length),
        remove_columns=train_dataset.column_names,
    )
    eval_dataset = eval_dataset.map(
        lambda row: tokenize_row(row, tokenizer, args.max_length),
        remove_columns=eval_dataset.column_names,
    )

    model = AutoModelForSequenceClassification.from_pretrained(
        args.model,
        num_labels=2,
        torch_dtype=torch.bfloat16,
    )

    trainer = Trainer(
        model=model,
        args=TrainingArguments(
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
        ),
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer,
        compute_metrics=compute_metrics,
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
