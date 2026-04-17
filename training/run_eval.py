#!/usr/bin/env python3
"""Run a benchmark manifest through a unified adapter interface."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DOCEDIT_DIR = ROOT / "attempt1" / "doc_edit_game_v2"
if str(DOCEDIT_DIR) not in sys.path:
    sys.path.insert(0, str(DOCEDIT_DIR))

from game.generator import generate_task  # noqa: E402
from game.grader import grade_task  # noqa: E402

from training.eval_harness import (  # noqa: E402
    BenchmarkCase,
    CopySourceAdapter,
    OpenAICompatibleChatAdapter,
    OpenAIResponsesAdapter,
    OracleAdapter,
    evaluate_cases,
    load_manifest,
    summarize,
    write_jsonl,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "training" / "manifests" / "docedit_benchmark_v1.json",
        help="Benchmark manifest path.",
    )
    parser.add_argument(
        "--split",
        default="validation",
        choices=("train", "validation", "test", "all"),
        help="Which split to evaluate.",
    )
    parser.add_argument(
        "--adapter",
        default="copy_source",
        choices=("copy_source", "oracle_target", "openai_responses", "openai_compatible"),
        help="Adapter backend to run.",
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=ROOT / "training" / "runs" / "latest_eval.jsonl",
        help="Where to write record-level results.",
    )
    parser.add_argument("--case-limit", type=int, default=0, help="Optional cap on evaluated cases.")
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--max-output-tokens", type=int, default=8_192)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    return parser


def task_loader(case: BenchmarkCase) -> dict:
    return generate_task(
        doc_seed=case.doc_seed,
        corruption_seed=case.corruption_seed,
        difficulty=case.difficulty,
        domain=case.domain,
    )


def task_grader(task: dict, edited_document: str) -> dict:
    return grade_task(
        current=edited_document,
        target=task["target"],
        original=task["source"],
        corruptions=task["corruptions"],
    )


def select_adapter(args):
    name = args.adapter
    if name == "copy_source":
        return CopySourceAdapter()
    if name == "oracle_target":
        return OracleAdapter()
    if name == "openai_responses":
        return OpenAIResponsesAdapter(
            model=args.model,
            api_key=args.api_key or None,
            api_key_env=args.api_key_env,
            max_output_tokens=args.max_output_tokens,
            temperature=args.temperature,
            timeout_seconds=args.timeout_seconds,
        )
    if name == "openai_compatible":
        return OpenAICompatibleChatAdapter(
            base_url=args.base_url,
            model=args.model,
            api_key=args.api_key or "EMPTY",
            max_tokens=args.max_output_tokens,
            temperature=args.temperature,
            timeout_seconds=args.timeout_seconds,
        )
    raise ValueError(f"Unknown adapter: {name}")


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    cases = load_manifest(args.manifest)
    if args.split != "all":
        cases = [case for case in cases if case.split == args.split]
    if args.case_limit:
        cases = cases[: args.case_limit]

    adapter = select_adapter(args)
    records = evaluate_cases(
        cases=cases,
        adapter=adapter,
        task_loader=task_loader,
        task_grader=task_grader,
    )
    write_jsonl(args.output_jsonl, records)

    summary = summarize(records)
    payload = {
        "manifest": str(args.manifest),
        "split": args.split,
        "adapter": adapter.name,
        "summary": summary,
        "output_jsonl": str(args.output_jsonl),
        "sample_records": [asdict(record) for record in records[:3]],
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
