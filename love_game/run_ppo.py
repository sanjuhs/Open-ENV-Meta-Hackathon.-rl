#!/usr/bin/env python3
"""Run PPO for Love Game using TRL experimental PPOTrainer."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from datasets import load_dataset
import torch
from transformers import AutoModelForCausalLM, AutoModelForSequenceClassification, AutoTokenizer
from trl.experimental.ppo import (
    AutoModelForCausalLMWithValueHead,
    PPOConfig,
    PPOTrainer,
)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-dataset", type=Path, required=True)
    parser.add_argument("--eval-dataset", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--reward-model", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-length", type=int, default=768)
    parser.add_argument("--response-length", type=int, default=72)
    parser.add_argument("--learning-rate", type=float, default=2e-6)
    parser.add_argument("--per-device-train-batch-size", type=int, default=4)
    parser.add_argument("--per-device-eval-batch-size", type=int, default=4)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=1)
    parser.add_argument("--num-train-epochs", type=float, default=1.0)
    parser.add_argument("--total-episodes", type=int)
    parser.add_argument("--logging-steps", type=int, default=5)
    parser.add_argument("--eval-steps", type=int, default=20)
    parser.add_argument("--save-steps", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-ppo-epochs", type=int, default=2)
    parser.add_argument("--num-mini-batches", type=int, default=1)
    parser.add_argument("--kl-coef", type=float, default=0.05)
    return parser


def tokenize_prompt_dataset(dataset, tokenizer, max_length: int):
    def mapper(row: dict) -> dict:
        encoded = tokenizer(
            row["prompt"],
            truncation=True,
            max_length=max_length,
            padding=False,
        )
        return {
            "input_ids": encoded["input_ids"],
            "attention_mask": encoded["attention_mask"],
        }

    return dataset.map(mapper, remove_columns=dataset.column_names)


def main() -> None:
    os.environ.setdefault("TRL_EXPERIMENTAL_SILENCE", "1")
    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    train_dataset = load_dataset("json", data_files=str(args.train_dataset), split="train")
    eval_dataset = load_dataset("json", data_files=str(args.eval_dataset), split="train")
    train_dataset = tokenize_prompt_dataset(train_dataset, tokenizer, args.max_length)
    eval_dataset = tokenize_prompt_dataset(eval_dataset, tokenizer, args.max_length)

    policy_model = AutoModelForCausalLM.from_pretrained(
        args.model,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    ref_model = AutoModelForCausalLM.from_pretrained(
        args.model,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    value_model = AutoModelForSequenceClassification.from_pretrained(
        args.model,
        num_labels=1,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    reward_model = AutoModelForSequenceClassification.from_pretrained(
        args.reward_model,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )

    trainer = PPOTrainer(
        args=PPOConfig(
            output_dir=str(args.output_dir),
            learning_rate=args.learning_rate,
            per_device_train_batch_size=args.per_device_train_batch_size,
            per_device_eval_batch_size=args.per_device_eval_batch_size,
            gradient_accumulation_steps=args.gradient_accumulation_steps,
            num_train_epochs=args.num_train_epochs,
            logging_steps=args.logging_steps,
            eval_steps=args.eval_steps,
            save_steps=args.save_steps,
            save_total_limit=2,
            bf16=True,
            report_to="none",
            seed=args.seed,
            response_length=args.response_length,
            num_ppo_epochs=args.num_ppo_epochs,
            num_mini_batches=args.num_mini_batches,
            kl_coef=args.kl_coef,
            stop_token="eos",
            total_episodes=args.total_episodes,
        ),
        processing_class=tokenizer,
        model=policy_model,
        ref_model=ref_model,
        reward_model=reward_model,
        value_model=value_model,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
    )

    trainer.train()
    trainer.save_model(str(args.output_dir))
    tokenizer.save_pretrained(args.output_dir)

    metrics_path = args.output_dir / "trainer_state.json"
    if metrics_path.exists():
        state = json.loads(metrics_path.read_text(encoding="utf-8"))
        (args.output_dir / "final_metrics.json").write_text(
            json.dumps({"log_history_tail": state.get("log_history", [])[-20:]}, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
