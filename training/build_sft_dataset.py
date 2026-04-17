#!/usr/bin/env python3
"""Build SFT and GRPO-ready datasets from the frozen benchmark manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.docedit_training import build_grpo_record, build_sft_record, task_from_case  # noqa: E402
from training.eval_harness import load_manifest  # noqa: E402


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "training" / "manifests" / "docedit_benchmark_v1.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "training" / "datasets",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=["train", "validation"],
        help="Splits to export.",
    )
    parser.add_argument(
        "--include-grpo",
        action="store_true",
        help="Also emit GRPO prompt-only datasets next to the SFT datasets.",
    )
    return parser


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def main() -> None:
    args = build_arg_parser().parse_args()
    cases = load_manifest(args.manifest)

    for split in args.splits:
        split_cases = [case for case in cases if case.split == split]
        sft_rows: list[dict] = []
        grpo_rows: list[dict] = []
        for case in split_cases:
            task = task_from_case(case)
            sft_rows.append(build_sft_record(case_id=case.case_id, task=task))
            if args.include_grpo:
                grpo_rows.append(build_grpo_record(case_id=case.case_id, task=task))

        sft_path = args.output_dir / f"sft_{split}.jsonl"
        write_jsonl(sft_path, sft_rows)
        print(f"Wrote {sft_path} ({len(sft_rows)} rows)")

        if args.include_grpo:
            grpo_path = args.output_dir / f"grpo_{split}.jsonl"
            write_jsonl(grpo_path, grpo_rows)
            print(f"Wrote {grpo_path} ({len(grpo_rows)} rows)")


if __name__ == "__main__":
    main()
