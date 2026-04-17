#!/usr/bin/env python3
"""Run local sample generation across Love Game checkpoints."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run_sample(script: Path, model_path: str | Path, dataset: Path, output_path: Path, limit: int, max_new_tokens: int) -> None:
    subprocess.run(
        [
            sys.executable,
            str(script),
            "--model-path",
            str(model_path),
            "--dataset",
            str(dataset),
            "--limit",
            str(limit),
            "--max-new-tokens",
            str(max_new_tokens),
            "--output-path",
            str(output_path),
        ],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--max-new-tokens", type=int, default=80)
    args = parser.parse_args()

    root = args.root
    love_dir = root / "love_game"
    checkpoints_dir = love_dir / "checkpoints" / args.snapshot
    split_dataset = love_dir / "splits" / args.snapshot / "sft_validation.jsonl"
    sample_script = love_dir / "sample_generations.py"
    out_dir = love_dir / "local_inference" / args.snapshot
    out_dir.mkdir(parents=True, exist_ok=True)

    model_map = {
        "base": "HuggingFaceTB/SmolLM2-135M-Instruct",
        "sft": checkpoints_dir / "smol_135m_sft_v3",
        "dpo": checkpoints_dir / "smol_135m_sft_dpo_v2",
        "grpo": checkpoints_dir / "smol_135m_sft_dpo_grpo_v1",
        "ppo": checkpoints_dir / "smol_135m_sft_dpo_ppo_v1",
    }

    written = {}
    for name, model in model_map.items():
        if isinstance(model, Path) and not model.exists():
            continue
        out_path = out_dir / f"{name}_samples.json"
        run_sample(sample_script, model, split_dataset, out_path, args.limit, args.max_new_tokens)
        written[name] = str(out_path)

    summary_path = out_dir / "manifest.json"
    summary_path.write_text(json.dumps(written, indent=2), encoding="utf-8")
    print(summary_path)


if __name__ == "__main__":
    main()
