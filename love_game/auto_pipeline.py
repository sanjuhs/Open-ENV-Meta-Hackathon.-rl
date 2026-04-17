#!/usr/bin/env python3
"""Watch Love Game dataset growth and launch training runs when thresholds are met."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from love_game.common import DATASETS_DIR, read_jsonl
from love_game.training_text import format_sft_example


DEFAULT_MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer-model", default=DEFAULT_MODEL)
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--sft-threshold", type=int, default=450_000)
    parser.add_argument("--dpo-threshold", type=int, default=100_000)
    parser.add_argument("--rm-threshold", type=int, default=120_000)
    parser.add_argument("--workspace", type=Path, default=ROOT)
    return parser


def count_tokens(tokenizer, text: str) -> int:
    return len(tokenizer(text, add_special_tokens=False)["input_ids"])


def dataset_totals(tokenizer) -> dict[str, int]:
    sft_rows = [format_sft_example(row) for row in read_jsonl(DATASETS_DIR / "sft_train.jsonl")]
    dpo_rows = read_jsonl(DATASETS_DIR / "rlhf_pairs_train.jsonl")
    rm_rows = read_jsonl(DATASETS_DIR / "rm_pointwise_train.jsonl")

    sft_total = sum(count_tokens(tokenizer, row["text"]) for row in sft_rows)
    dpo_total = sum(
        count_tokens(tokenizer, row["prompt"])
        + count_tokens(tokenizer, row["preferred_response"])
        + count_tokens(tokenizer, row["dispreferred_response"])
        for row in dpo_rows
    )
    rm_total = sum(
        count_tokens(tokenizer, f"{row['prompt']}\n\nResponse:\n{row['response']}")
        for row in rm_rows
    )
    return {
        "sft_text_tokens": sft_total,
        "dpo_pair_tokens": dpo_total,
        "rm_pointwise_tokens": rm_total,
    }


def run_command(command: list[str], cwd: Path, log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n=== RUN {' '.join(command)} ===\n")
        handle.flush()
        proc = subprocess.run(command, cwd=cwd, stdout=handle, stderr=subprocess.STDOUT)
    return proc.returncode


def main() -> None:
    args = build_parser().parse_args()
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer_model, trust_remote_code=True)
    workspace = args.workspace
    runs_dir = workspace / "love_game" / "auto_runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    sft_output = workspace / "love_game" / "checkpoints" / "smol_135m_sft_auto_v3"
    dpo_output = workspace / "love_game" / "checkpoints" / "smol_135m_dpo_auto_v3"
    rm_output = workspace / "love_game" / "checkpoints" / "reward_model_distilroberta_auto_v2"
    state_path = runs_dir / "auto_pipeline_state.json"

    while True:
        totals = dataset_totals(tokenizer)
        state = {
            "totals": totals,
            "sft_ready": totals["sft_text_tokens"] >= args.sft_threshold,
            "dpo_ready": totals["dpo_pair_tokens"] >= args.dpo_threshold,
            "rm_ready": totals["rm_pointwise_tokens"] >= args.rm_threshold,
            "sft_exists": sft_output.exists(),
            "dpo_exists": dpo_output.exists(),
            "rm_exists": rm_output.exists(),
        }
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        print(json.dumps(state), flush=True)

        if state["sft_ready"] and not state["sft_exists"]:
            run_command(
                ["python3", "love_game/build_training_splits.py"],
                cwd=workspace,
                log_path=runs_dir / "auto_sft.log",
            )
            run_command(
                [
                    "python3",
                    "love_game/run_sft_full.py",
                    "--train-dataset",
                    "love_game/splits/sft_train.jsonl",
                    "--eval-dataset",
                    "love_game/splits/sft_validation.jsonl",
                    "--model",
                    DEFAULT_MODEL,
                    "--output-dir",
                    str(sft_output),
                    "--max-length",
                    "768",
                    "--learning-rate",
                    "3e-5",
                    "--per-device-train-batch-size",
                    "16",
                    "--per-device-eval-batch-size",
                    "16",
                    "--gradient-accumulation-steps",
                    "1",
                    "--num-train-epochs",
                    "6",
                    "--logging-steps",
                    "5",
                    "--eval-steps",
                    "20",
                    "--save-steps",
                    "50",
                ],
                cwd=workspace,
                log_path=runs_dir / "auto_sft.log",
            )

        if state["rm_ready"] and not state["rm_exists"]:
            run_command(
                ["python3", "love_game/build_training_splits.py"],
                cwd=workspace,
                log_path=runs_dir / "auto_rm.log",
            )
            run_command(
                [
                    "python3",
                    "love_game/run_reward_model_transformer.py",
                    "--train-dataset",
                    "love_game/splits/rm_pointwise_train.jsonl",
                    "--eval-dataset",
                    "love_game/splits/rm_pointwise_validation.jsonl",
                    "--model",
                    "distilroberta-base",
                    "--output-dir",
                    str(rm_output),
                    "--max-length",
                    "384",
                    "--learning-rate",
                    "2e-5",
                    "--per-device-train-batch-size",
                    "32",
                    "--per-device-eval-batch-size",
                    "32",
                    "--num-train-epochs",
                    "4",
                    "--logging-steps",
                    "2",
                    "--eval-steps",
                    "5",
                    "--save-steps",
                    "10",
                ],
                cwd=workspace,
                log_path=runs_dir / "auto_rm.log",
            )

        if state["dpo_ready"] and not state["dpo_exists"] and sft_output.exists():
            run_command(
                ["python3", "love_game/build_training_splits.py"],
                cwd=workspace,
                log_path=runs_dir / "auto_dpo.log",
            )
            run_command(
                [
                    "python3",
                    "love_game/run_dpo_full.py",
                    "--train-dataset",
                    "love_game/splits/rlhf_train.jsonl",
                    "--eval-dataset",
                    "love_game/splits/rlhf_validation.jsonl",
                    "--model",
                    str(sft_output),
                    "--output-dir",
                    str(dpo_output),
                    "--max-length",
                    "768",
                    "--learning-rate",
                    "3e-5",
                    "--per-device-train-batch-size",
                    "8",
                    "--per-device-eval-batch-size",
                    "8",
                    "--gradient-accumulation-steps",
                    "1",
                    "--num-train-epochs",
                    "4",
                    "--logging-steps",
                    "2",
                    "--eval-steps",
                    "5",
                    "--save-steps",
                    "10",
                ],
                cwd=workspace,
                log_path=runs_dir / "auto_dpo.log",
            )

        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
