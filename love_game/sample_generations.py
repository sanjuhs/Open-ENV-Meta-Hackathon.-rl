#!/usr/bin/env python3
"""Generate sample replies from a base or fine-tuned Love Game model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from love_game.common import read_jsonl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--max-new-tokens", type=int, default=80)
    parser.add_argument("--output-path", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rows = read_jsonl(args.dataset)[: args.limit]

    tokenizer = AutoTokenizer.from_pretrained(args.model_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.model_path,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    model.eval()

    outputs = []
    for row in rows:
        prompt = row["prompt"]
        encoded = tokenizer(prompt, return_tensors="pt").to(model.device)
        generated = model.generate(
            **encoded,
            max_new_tokens=args.max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
        text = tokenizer.decode(generated[0], skip_special_tokens=True)
        outputs.append(
            {
                "scenario_id": row.get("scenario_id", ""),
                "prompt": prompt,
                "reference": row.get("completion") or row.get("reference_reply", ""),
                "generated": text[len(prompt) :].strip() if text.startswith(prompt) else text,
            }
        )

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(json.dumps(outputs, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {args.output_path}")


if __name__ == "__main__":
    main()
