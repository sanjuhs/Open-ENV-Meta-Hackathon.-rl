#!/usr/bin/env python3
"""Download and sanity-check the recommended DocEdit training models."""

from __future__ import annotations

import argparse

from huggingface_hub import snapshot_download
from transformers import AutoConfig, AutoTokenizer


MODEL_PRESETS = {
    "tiny": "HuggingFaceTB/SmolLM2-135M-Instruct",
    "medium": "Qwen/Qwen2.5-3B-Instruct",
    "experimental": "google/gemma-4-E2B-it",
}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models",
        nargs="+",
        default=["tiny", "medium", "experimental"],
        help="Preset names or explicit model IDs.",
    )
    parser.add_argument("--allow-patterns", nargs="+")
    return parser


def resolve_model(name: str) -> str:
    return MODEL_PRESETS.get(name, name)


def main() -> None:
    args = build_arg_parser().parse_args()
    for item in args.models:
        model_id = resolve_model(item)
        snapshot_path = snapshot_download(repo_id=model_id, allow_patterns=args.allow_patterns)
        tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        config = AutoConfig.from_pretrained(model_id, trust_remote_code=True)
        print(
            f"{model_id}\n"
            f"  snapshot: {snapshot_path}\n"
            f"  model_type: {getattr(config, 'model_type', 'unknown')}\n"
            f"  vocab_size: {getattr(config, 'vocab_size', 'unknown')}\n"
            f"  tokenizer: {tokenizer.__class__.__name__}"
        )


if __name__ == "__main__":
    main()
