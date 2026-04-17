#!/usr/bin/env python3
"""Run GRPO for Love Game with learned and/or rule-based rewards."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoModelForSequenceClassification,
    AutoTokenizer,
)
from trl import GRPOConfig, GRPOTrainer

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from love_game.reward import score_reply


DEFAULT_MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-dataset", type=Path, required=True)
    parser.add_argument("--eval-dataset", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reward-model", type=Path)
    parser.add_argument("--num-train-epochs", type=float, default=2.0)
    parser.add_argument("--max-steps", type=int, default=-1)
    parser.add_argument("--learning-rate", type=float, default=2e-6)
    parser.add_argument("--per-device-train-batch-size", type=int, default=4)
    parser.add_argument("--per-device-eval-batch-size", type=int, default=4)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=1)
    parser.add_argument("--max-completion-length", type=int, default=96)
    parser.add_argument("--num-generations", type=int, default=4)
    parser.add_argument("--logging-steps", type=int, default=5)
    parser.add_argument("--eval-steps", type=int, default=20)
    parser.add_argument("--save-steps", type=int, default=40)
    parser.add_argument("--eval-strategy", default="steps")
    parser.add_argument("--save-strategy", default="steps")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--rule-weight", type=float, default=1.0)
    parser.add_argument("--model-weight", type=float, default=0.25)
    parser.add_argument("--disable-rule-reward", action="store_true")
    parser.add_argument("--reward-max-length", type=int, default=512)
    return parser


def normalize_prompt_row(row: dict) -> dict:
    return {
        "prompt": row["prompt"],
        "scenario_id": row.get("scenario_id", ""),
        "tags": row.get("tags", []),
        "conversation": row.get("conversation", []),
        "reference_reply": row.get("reference_reply", ""),
    }


class LearnedRewardScorer:
    """Callable reward scorer backed by a sequence classifier."""

    def __init__(self, model_path: Path, max_length: int):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
        )
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        self.max_length = max_length
        self.__name__ = "learned_reward_model"

    def __call__(self, prompts, completions, **kwargs):
        del kwargs
        texts = [f"{prompt}\n\nResponse:\n{completion}" for prompt, completion in zip(prompts, completions, strict=True)]
        encoded = self.tokenizer(
            texts,
            truncation=True,
            max_length=self.max_length,
            padding=True,
            return_tensors="pt",
        ).to(self.device)
        with torch.inference_mode():
            logits = self.model(**encoded).logits
        if logits.ndim == 1:
            reward = logits
        elif logits.shape[-1] == 1:
            reward = logits[:, 0]
        else:
            reward = logits[:, 1] - logits[:, 0]
        return reward.float().cpu().tolist()


def rule_reward(prompts, completions, **kwargs):
    del prompts, kwargs
    return [score_reply(completion).total for completion in completions]


def main() -> None:
    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    train_dataset = load_dataset("json", data_files=str(args.train_dataset), split="train").map(normalize_prompt_row)
    eval_dataset = load_dataset("json", data_files=str(args.eval_dataset), split="train").map(normalize_prompt_row)

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    model.config.use_cache = False

    reward_funcs: list = []
    reward_processing_classes: list = []
    reward_weights: list[float] = []

    if args.reward_model is not None:
        reward_funcs.append(LearnedRewardScorer(args.reward_model, max_length=args.reward_max_length))
        reward_processing_classes.append(None)
        reward_weights.append(args.model_weight)

    if not args.disable_rule_reward:
        reward_funcs.append(rule_reward)
        reward_processing_classes.append(None)
        reward_weights.append(args.rule_weight)

    if not reward_funcs:
        raise ValueError("At least one reward function must be enabled.")

    trainer = GRPOTrainer(
        model=model,
        reward_funcs=reward_funcs,
        reward_processing_classes=reward_processing_classes,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
        args=GRPOConfig(
            output_dir=str(args.output_dir),
            learning_rate=args.learning_rate,
            per_device_train_batch_size=args.per_device_train_batch_size,
            per_device_eval_batch_size=args.per_device_eval_batch_size,
            gradient_accumulation_steps=args.gradient_accumulation_steps,
            num_train_epochs=args.num_train_epochs,
            max_steps=args.max_steps,
            logging_steps=args.logging_steps,
            eval_steps=args.eval_steps,
            save_steps=args.save_steps,
            eval_strategy=args.eval_strategy,
            save_strategy=args.save_strategy,
            save_total_limit=3,
            bf16=True,
            report_to="none",
            seed=args.seed,
            max_completion_length=args.max_completion_length,
            num_generations=args.num_generations,
            reward_weights=reward_weights,
            use_vllm=False,
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
