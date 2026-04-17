#!/usr/bin/env python3
"""Run a first-pass GRPO loop for DocEdit direct-rewrite training."""

from __future__ import annotations

import argparse
from pathlib import Path

from datasets import load_dataset
from peft import AutoPeftModelForCausalLM, LoraConfig
from transformers import AutoTokenizer
from trl import GRPOConfig, GRPOTrainer

from training.docedit_training import extract_document_from_completion, score_document


DEFAULT_MODEL = "Qwen/Qwen2.5-3B-Instruct"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-dataset", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--sft-adapter")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--per-device-train-batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=5e-6)
    parser.add_argument("--max-prompt-length", type=int, default=6_144)
    parser.add_argument("--max-completion-length", type=int, default=2_048)
    parser.add_argument("--num-generations", type=int, default=4)
    parser.add_argument("--max-steps", type=int, default=100)
    parser.add_argument("--save-steps", type=int, default=25)
    parser.add_argument("--logging-steps", type=int, default=5)
    parser.add_argument("--use-vllm", action="store_true")
    parser.add_argument("--vllm-mode", default="colocate", choices=("colocate", "server"))
    parser.add_argument("--vllm-server-host", default="")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()

    train_dataset = load_dataset("json", data_files=str(args.train_dataset), split="train")

    tokenizer = AutoTokenizer.from_pretrained(args.sft_adapter or args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    if args.sft_adapter:
        model = AutoPeftModelForCausalLM.from_pretrained(
            args.sft_adapter,
            is_trainable=True,
            trust_remote_code=True,
        )
    else:
        model = args.model

    def structural_reward(completions, source, target, corruptions_json, **kwargs):
        rewards = []
        for completion, item_source, item_target, item_corruptions in zip(
            completions,
            source,
            target,
            corruptions_json,
        ):
            edited_document = extract_document_from_completion(completion)
            score = score_document(
                source=item_source,
                target=item_target,
                corruptions=item_corruptions,
                edited_document=edited_document,
            )
            reward = score["composite_score"]
            if score["similarity"] >= 0.999:
                reward += 1.0
            rewards.append(reward)
        return rewards

    def format_reward(completions, **kwargs):
        rewards = []
        for completion in completions:
            reward = 0.0
            lowered = completion.lower()
            if "```" in completion:
                reward -= 0.25
            if "<think>" in lowered or "assistant:" in lowered:
                reward -= 0.25
            rewards.append(reward)
        return rewards

    training_args = GRPOConfig(
        output_dir=str(args.output_dir),
        per_device_train_batch_size=args.per_device_train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        max_steps=args.max_steps,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        save_total_limit=3,
        bf16=True,
        max_prompt_length=args.max_prompt_length,
        max_completion_length=args.max_completion_length,
        num_generations=args.num_generations,
        report_to="none",
        remove_unused_columns=False,
        use_vllm=args.use_vllm,
        vllm_mode=args.vllm_mode,
    )
    if args.vllm_server_host:
        training_args.vllm_server_host = args.vllm_server_host

    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_funcs=[structural_reward, format_reward],
        args=training_args,
        train_dataset=train_dataset,
        peft_config=None
        if args.sft_adapter
        else LoraConfig(
            r=32,
            lora_alpha=64,
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules="all-linear",
        ),
    )
    trainer.train()
    trainer.save_model()
    tokenizer.save_pretrained(args.output_dir)


if __name__ == "__main__":
    main()
