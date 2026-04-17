#!/usr/bin/env python3
"""Generate more Love Game data in parallel and merge it with deduplication."""

from __future__ import annotations

import argparse
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from love_game.common import DATASETS_DIR, dedupe_rows, read_jsonl, write_jsonl
from love_game.generate_datasets import (
    SCENARIO_SEEDS,
    build_prompt,
    load_api_key,
    parse_json_array,
    post_responses,
)
from love_game.reward import compact_text, score_reply


DIVERSITY_AXES = [
    "late-night reassurance",
    "jealousy but playful",
    "post-gym tired texting",
    "Bangalore rain plan changes",
    "missing each other after a long commute",
    "teasing after a stupid joke",
    "fight repair with quick forgiveness",
    "food cravings and dosa talk",
    "walking-date planning",
    "MBA anxiety mixed with work stress",
    "reels and dance video chatter",
    "family visit to Mysore",
    "grandmother mention and soft family affection",
    "whitefield traffic or metro complaints",
    "clingy but funny texting bursts",
    "small possessiveness without toxicity",
    "ice-cream bribery",
    "football banter during commute",
]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=ROOT / "love_game" / "character_profile.json")
    parser.add_argument("--output-dir", type=Path, default=DATASETS_DIR)
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--sft-count", type=int, default=120)
    parser.add_argument("--dpo-count", type=int, default=90)
    parser.add_argument("--rl-count", type=int, default=90)
    parser.add_argument("--batch-size", type=int, default=6)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    return parser


def mode_file(mode: str) -> str:
    return {
        "sft": "sft_train.jsonl",
        "dpo": "dpo_train.jsonl",
        "rl": "rl_train.jsonl",
    }[mode]


def enrich_rl_rows(rows: list[dict]) -> list[dict]:
    enriched = []
    for row in rows:
        reply = compact_text(row.get("candidate_reply", ""))
        enriched.append({**row, "candidate_reply": reply, "reward": score_reply(reply).to_dict()})
    return enriched


def prompt_with_diversity(profile: dict, mode: str, count: int, rng: random.Random, existing_rows: list[dict]) -> str:
    seeds = SCENARIO_SEEDS[:] + [f"Extra axis: {item}" for item in DIVERSITY_AXES]
    rng.shuffle(seeds)
    prompt = build_prompt(profile, mode, count, seeds[: min(12, len(seeds))])
    sample_existing = []
    for row in rng.sample(existing_rows, k=min(6, len(existing_rows))) if existing_rows else []:
        snippet = row.get("scenario_id", "")
        user = compact_text(row.get("user_message", ""))[:100]
        sample_existing.append({"scenario_id": snippet, "user_message": user})
    extra = {
        "instructions": [
            "Make the scenarios materially different from the existing examples.",
            "Vary tone, pacing, emotional intensity, and context.",
            "Do not reuse the same scenario_id or close paraphrases of existing user messages.",
            "Some replies can be mildly chaotic, funny, clingy, or impulsive, but still in character.",
        ],
        "avoid_examples": sample_existing,
    }
    return prompt + "\n\nExtra diversity guidance:\n" + json.dumps(extra, ensure_ascii=False, indent=2)


def generate_batch(
    *,
    api_key: str,
    model: str,
    profile: dict,
    mode: str,
    batch_size: int,
    seed_value: int,
    existing_rows: list[dict],
) -> list[dict]:
    rng = random.Random(seed_value)
    prompt = prompt_with_diversity(profile, mode, batch_size, rng, existing_rows)
    raw = post_responses(api_key=api_key, model=model, prompt=prompt)
    rows = parse_json_array(raw)
    if mode == "rl":
        rows = enrich_rl_rows(rows)
    return rows


def main() -> None:
    args = build_arg_parser().parse_args()
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    api_key = load_api_key(args.api_key_env)
    job_rng = random.Random(20260418)

    counts = {"sft": args.sft_count, "dpo": args.dpo_count, "rl": args.rl_count}
    manifest: dict[str, dict] = {}
    for mode, target_new in counts.items():
        path = args.output_dir / mode_file(mode)
        existing = read_jsonl(path)
        merged = list(existing)
        added = 0
        attempts = 0
        max_attempts = max(8, (target_new // max(1, args.batch_size)) * 4)

        print(f"\n=== Expanding {mode} ===")
        print(f"Starting rows: {len(existing)} | Target new unique rows: {target_new}")

        while added < target_new and attempts < max_attempts:
            batch_jobs = min(args.workers, max(1, (target_new - added + args.batch_size - 1) // args.batch_size))
            with ThreadPoolExecutor(max_workers=batch_jobs) as pool:
                futures = []
                for _ in range(batch_jobs):
                    seed_value = job_rng.randint(0, 10_000_000)
                    futures.append(
                        pool.submit(
                            generate_batch,
                            api_key=api_key,
                            model=args.model,
                            profile=profile,
                            mode=mode,
                            batch_size=min(args.batch_size, target_new - added),
                            seed_value=seed_value,
                            existing_rows=merged,
                        )
                    )
                for future in as_completed(futures):
                    attempts += 1
                    batch = future.result()
                    before = len(merged)
                    merged.extend(batch)
                    merged = dedupe_rows(merged)
                    gained = len(merged) - before
                    added += max(0, gained)
                    print(
                        f"{mode}: batch returned {len(batch)} rows, "
                        f"kept {gained} new unique rows, total added={added}/{target_new}"
                    )
                    if added >= target_new:
                        break

        write_jsonl(path, merged)
        print(f"Finished {mode}. Final rows: {len(merged)}")
        manifest[mode] = {
            "count": len(merged),
            "path": str(path),
            "model": args.model,
        }

    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {(args.output_dir / 'manifest.json')}")


if __name__ == "__main__":
    main()
