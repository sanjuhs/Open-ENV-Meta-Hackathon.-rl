#!/usr/bin/env python3
"""Scale Love Game datasets to target token budgets with multi-turn synthetic data."""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from json import JSONDecodeError

from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from love_game.common import DATASETS_DIR, dedupe_rows, read_jsonl, write_jsonl
from love_game.generate_datasets import load_api_key, parse_json_array, post_responses
from love_game.prepare_training_sets import main as prepare_training_sets_main
from love_game.reward import compact_text, score_reply
from love_game.training_text import build_prompt_from_row, format_sft_example


API_MODEL_DEFAULT = "gpt-5.4-mini"
TOKENIZER_MODEL_DEFAULT = "HuggingFaceTB/SmolLM2-135M-Instruct"

MULTITURN_SEEDS = [
    "A long Bangalore commute conversation that keeps getting interrupted by metro announcements.",
    "A late-night texting exchange where the user is overthinking and Aditi replies in three or four bursty messages.",
    "A small fight that gets repaired over several back-and-forth messages with teasing and softness.",
    "A weekend planning chat that drifts into dosa cravings, walking plans, and random jokes.",
    "A vulnerable conversation about MBA plans, burnout, and future anxiety over multiple turns.",
    "A clingy but funny texting exchange after one person replies slowly for a couple of hours.",
    "A family-oriented chat involving grandmother, parents, Bangalore neighborhoods, and being slightly dramatic.",
    "A football conversation that becomes personal, playful, and mildly chaotic over several turns.",
    "A post-gym conversation with food cravings, body image jokes, and affectionate teasing.",
    "A conversation after an awkward social interaction where Aditi gets briefly angry, then soft again.",
    "A long walk-date planning conversation with weather, location, food stops, and emotional undertones.",
    "A mixed conversation about work stress, dance reels, and wanting comfort instead of advice.",
]


def summarize_profile(profile: dict) -> str:
    language = profile.get("language_style", {})
    locations = profile.get("locations", {})
    interests = ", ".join(profile.get("interests", [])[:8])
    traits = ", ".join(profile.get("traits", [])[:8])
    style_tags = ", ".join(language.get("style_tags", [])[:5])
    return (
        f'{profile.get("name", "Aditi")}, fictional, {profile.get("age", 26)} years old, '
        f'{profile.get("profession", "graphic designer")}, Bangalore-based. '
        f'Commutes {locations.get("home_origin", "Jayanagar")} to {locations.get("commute_to", "Whitefield")} by metro. '
        f'Interests: {interests}. Traits: {traits}. '
        f'Voice: mostly English with light Hinglish/Kannada mixing; style tags: {style_tags}. '
        "Energetic, playful, specific, urban, emotionally responsive, occasionally profane in English."
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=ROOT / "love_game" / "character_profile.json")
    parser.add_argument("--output-dir", type=Path, default=DATASETS_DIR)
    parser.add_argument("--api-model", default=API_MODEL_DEFAULT)
    parser.add_argument("--tokenizer-model", default=TOKENIZER_MODEL_DEFAULT)
    parser.add_argument("--target-sft-tokens", type=int, default=2_000_000)
    parser.add_argument("--target-dpo-tokens", type=int, default=2_000_000)
    parser.add_argument("--target-ppo-prompt-tokens", type=int, default=2_000_000)
    parser.add_argument("--target-rl-tokens", type=int, default=1_000_000)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--workers", type=int, default=50)
    parser.add_argument("--min-batch-size", type=int, default=1)
    parser.add_argument("--max-retries", type=int, default=8)
    parser.add_argument("--backoff-base-seconds", type=float, default=2.0)
    parser.add_argument("--request-timeout-seconds", type=int, default=180)
    parser.add_argument("--save-every-batches", type=int, default=4)
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    return parser


def schema_for_mode(mode: str) -> dict:
    base_string = {"type": "string"}
    conversation_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "role": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["role", "content"],
        },
    }
    if mode == "sft":
        return {
            "name": "love_game_sft_row",
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "scenario_id": base_string,
                    "context": base_string,
                    "conversation": conversation_schema,
                    "user_message": base_string,
                    "assistant_reply": base_string,
                    "tags": {"type": "array", "items": base_string},
                },
                "required": ["scenario_id", "context", "conversation", "user_message", "assistant_reply", "tags"],
            },
        }
    if mode == "dpo":
        return {
            "name": "love_game_dpo_row",
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "scenario_id": base_string,
                    "context": base_string,
                    "conversation": conversation_schema,
                    "user_message": base_string,
                    "chosen": base_string,
                    "rejected": base_string,
                    "preference_reason": base_string,
                },
                "required": ["scenario_id", "context", "conversation", "user_message", "chosen", "rejected", "preference_reason"],
            },
        }
    return {
        "name": "love_game_rl_row",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "scenario_id": base_string,
                "context": base_string,
                "conversation": conversation_schema,
                "user_message": base_string,
                "candidate_reply": base_string,
                "latent_state": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "trust": {"type": "number"},
                        "warmth": {"type": "number"},
                        "energy": {"type": "number"},
                        "jealousy": {"type": "number"},
                    },
                    "required": ["trust", "warmth", "energy", "jealousy"],
                },
                "expected_goodness": {"type": "number"},
                "notes": base_string,
            },
            "required": ["scenario_id", "context", "conversation", "user_message", "candidate_reply", "latent_state", "expected_goodness", "notes"],
        },
    }


def build_prompt(profile: dict, mode: str, count: int, seeds: list[str], avoid_rows: list[dict]) -> str:
    profile_summary = summarize_profile(profile)
    seed_lines = "\n".join(f"- {seed}" for seed in seeds)
    avoid = []
    for row in avoid_rows[:4]:
        avoid.append(
            {
                "scenario_id": row.get("scenario_id", ""),
                "user_message": compact_text(row.get("user_message", ""))[:120],
            }
        )
    common = f"""
You are generating high-volume synthetic conversation data for a fictional character training run.

Character summary:
{profile_summary}

Important goals:
- Make these examples multi-turn and information-dense.
- Most examples should include 3 to 8 previous turns before the final user message.
- Keep the voice strongly consistent and playful.
- Use specific Bangalore details, commuting details, walking, food, gym, football, work stress, reels, family, and silly jokes.
- Avoid robotic phrasing, disclaimers, or generic therapy language.
- Do not repeat scenario_id values or close paraphrases of existing examples.

Scenario inspirations:
{seed_lines}

Avoid making examples too similar to:
{json.dumps(avoid, ensure_ascii=False, indent=2)}
""".strip()

    row_word = "object" if count == 1 else "objects"
    if mode == "sft":
        return common + f"""

Generate exactly {count} JSON {row_word} for supervised fine-tuning.
Each object must have:
- scenario_id
- context
- conversation: list of previous turns, each with role and content
- user_message
- assistant_reply
- tags

Rules:
- Make the conversation history meaningful, not filler.
- The final assistant_reply should feel like the next natural message in that conversation.
- Replies can occasionally use words like "fuck", but not every time.
- Return valid JSON only.
"""
    if mode == "dpo":
        return common + f"""

Generate exactly {count} JSON {row_word} for DPO / RLHF pair training.
Each object must have:
- scenario_id
- context
- conversation: list of previous turns, each with role and content
- user_message
- chosen
- rejected
- preference_reason

Rules:
- Make the chosen response clearly more in-character, more emotionally appropriate, and more specific.
- Make the rejected response too bland, too generic, too formal, slightly off-tone, or slightly repetitive.
- Return valid JSON only.
"""
    return common + f"""

Generate exactly {count} JSON {row_word} for GRPO / rollout-style training.
Each object must have:
- scenario_id
- context
- conversation: list of previous turns, each with role and content
- user_message
- candidate_reply
- latent_state
- expected_goodness
- notes

Rules:
- candidate_reply should be plausible but not always perfect.
- Keep the conversation history rich so the final prompt is long and interesting.
- Return valid JSON only.
"""


def count_sft_tokens(tokenizer, rows: list[dict]) -> int:
    total = 0
    for row in rows:
        formatted = format_sft_example(row)
        total += len(tokenizer(formatted["text"], add_special_tokens=False)["input_ids"])
    return total


def count_dpo_tokens(tokenizer, rows: list[dict]) -> int:
    total = 0
    for row in rows:
        prompt = build_prompt_from_row(row)
        total += len(tokenizer(prompt, add_special_tokens=False)["input_ids"])
        total += len(tokenizer(row["chosen"], add_special_tokens=False)["input_ids"])
        total += len(tokenizer(row["rejected"], add_special_tokens=False)["input_ids"])
    return total


def count_ppo_prompt_tokens(tokenizer, sft_rows: list[dict]) -> int:
    total = 0
    for row in sft_rows:
        prompt = build_prompt_from_row(row)
        total += len(tokenizer(prompt, add_special_tokens=False)["input_ids"])
    return total


def count_rl_tokens(tokenizer, rows: list[dict]) -> int:
    total = 0
    for row in rows:
        prompt = build_prompt_from_row(row)
        total += len(tokenizer(prompt, add_special_tokens=False)["input_ids"])
        total += len(tokenizer(row["candidate_reply"], add_special_tokens=False)["input_ids"])
    return total


def enrich_rl_rows(rows: list[dict]) -> list[dict]:
    enriched = []
    for row in rows:
        reply = compact_text(row.get("candidate_reply", ""))
        enriched.append({**row, "candidate_reply": reply, "reward": score_reply(reply).to_dict()})
    return enriched


def make_job_prompt(profile: dict, mode: str, count: int, seed_value: int, existing_rows: list[dict]) -> str:
    rng = random.Random(seed_value)
    seeds = MULTITURN_SEEDS[:]
    rng.shuffle(seeds)
    sampled_existing = rng.sample(existing_rows, k=min(len(existing_rows), 4)) if existing_rows else []
    return build_prompt(profile, mode, count, seeds[: min(6, len(seeds))], sampled_existing)


def generate_batch(
    api_key: str,
    api_model: str,
    profile: dict,
    mode: str,
    count: int,
    seed_value: int,
    existing_rows: list[dict],
    *,
    min_batch_size: int,
    max_retries: int,
    backoff_base_seconds: float,
    request_timeout_seconds: int,
) -> list[dict]:
    current_count = count
    for attempts in range(1, max_retries + 1):
        prompt = make_job_prompt(profile, mode, current_count, seed_value + attempts, existing_rows)
        try:
            raw = post_responses(
                api_key=api_key,
                model=api_model,
                prompt=prompt,
                max_output_tokens=None,
                timeout_seconds=request_timeout_seconds,
                json_schema=schema_for_mode(mode),
            )
            parsed = json.loads(raw)
            rows = parsed if isinstance(parsed, list) else [parsed]
            if mode == "rl":
                rows = enrich_rl_rows(rows)
            return rows
        except (JSONDecodeError, subprocess.CalledProcessError) as exc:
            current_count = max(min_batch_size, current_count // 2)
            if attempts >= max_retries:
                break
            sleep_seconds = min(90.0, backoff_base_seconds * (2 ** (attempts - 1)) + random.random())
            print(
                json.dumps(
                    {
                        "mode": mode,
                        "event": "retry",
                        "attempt": attempts,
                        "next_batch_size": current_count,
                        "sleep_seconds": round(sleep_seconds, 2),
                        "error_type": type(exc).__name__,
                    }
                ),
                flush=True,
            )
            time.sleep(sleep_seconds)
    raise RuntimeError(f"Failed to generate parseable {mode} batch after retries")


def write_mode_snapshot(output_dir: Path, mode: str, rows: list[dict]) -> None:
    write_jsonl(output_dir / f"{mode}_train.jsonl", rows)


def refresh_derived_datasets() -> None:
    prepare_training_sets_main()


def main() -> None:
    args = build_arg_parser().parse_args()
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    api_key = load_api_key(args.api_key_env)
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer_model, trust_remote_code=True)

    datasets = {
        "sft": read_jsonl(args.output_dir / "sft_train.jsonl"),
        "dpo": read_jsonl(args.output_dir / "dpo_train.jsonl"),
        "rl": read_jsonl(args.output_dir / "rl_train.jsonl"),
    }
    lock = threading.Lock()
    rng = random.Random(20260418)

    def current_counts() -> dict[str, int]:
        return {
            "sft_tokens": count_sft_tokens(tokenizer, datasets["sft"]),
            "dpo_tokens": count_dpo_tokens(tokenizer, datasets["dpo"]),
            "ppo_prompt_tokens": count_ppo_prompt_tokens(tokenizer, datasets["sft"]),
            "rl_tokens": count_rl_tokens(tokenizer, datasets["rl"]),
        }

    targets = {
        "sft": args.target_sft_tokens,
        "dpo": args.target_dpo_tokens,
        "rl": args.target_rl_tokens,
    }

    print("Initial counts:")
    print(json.dumps(current_counts(), indent=2))

    def needs_more(mode: str) -> bool:
        counts = current_counts()
        if mode == "sft":
            return counts["sft_tokens"] < targets["sft"] or counts["ppo_prompt_tokens"] < args.target_ppo_prompt_tokens
        if mode == "dpo":
            return counts["dpo_tokens"] < targets["dpo"]
        return counts["rl_tokens"] < targets["rl"]

    batches_since_save = 0

    for mode in ("sft", "dpo", "rl"):
        print(f"\n=== Scaling {mode} ===")
        while needs_more(mode):
            batch_jobs = args.workers
            futures = []
            with ThreadPoolExecutor(max_workers=batch_jobs) as pool:
                for _ in range(batch_jobs):
                    seed_value = rng.randint(0, 10_000_000)
                    existing_snapshot = list(datasets[mode])
                    futures.append(
                        pool.submit(
                            generate_batch,
                            api_key,
                            args.api_model,
                            profile,
                            mode,
                            args.batch_size,
                            seed_value,
                            existing_snapshot,
                            min_batch_size=args.min_batch_size,
                            max_retries=args.max_retries,
                            backoff_base_seconds=args.backoff_base_seconds,
                            request_timeout_seconds=args.request_timeout_seconds,
                        )
                    )
                for future in as_completed(futures):
                    try:
                        batch = future.result()
                    except Exception as exc:
                        print(
                            json.dumps(
                                {
                                    "mode": mode,
                                    "event": "batch_failed",
                                    "error_type": type(exc).__name__,
                                    "message": str(exc),
                                }
                            ),
                            flush=True,
                        )
                        continue
                    with lock:
                        before = len(datasets[mode])
                        datasets[mode].extend(batch)
                        datasets[mode] = dedupe_rows(datasets[mode])
                        gained = len(datasets[mode]) - before
                        counts = current_counts()
                        print(
                            json.dumps(
                                {
                                    "mode": mode,
                                    "batch_rows": len(batch),
                                    "new_unique_rows": gained,
                                    "totals": counts,
                                }
                            )
                        )
                        batches_since_save += 1
                        if batches_since_save >= args.save_every_batches:
                            write_mode_snapshot(args.output_dir, mode, datasets[mode])
                            refresh_derived_datasets()
                            batches_since_save = 0
                    if not needs_more(mode):
                        break

            write_mode_snapshot(args.output_dir, mode, datasets[mode])
            refresh_derived_datasets()
            if not needs_more(mode):
                break

    # Rebuild derived datasets after scaling.
    refresh_derived_datasets()

    final_counts = current_counts()
    summary_path = args.output_dir / "scale_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "api_model": args.api_model,
                "tokenizer_model": args.tokenizer_model,
                "targets": {
                    "sft_tokens": args.target_sft_tokens,
                    "dpo_tokens": args.target_dpo_tokens,
                    "ppo_prompt_tokens": args.target_ppo_prompt_tokens,
                    "rl_tokens": args.target_rl_tokens,
                },
                "final_counts": final_counts,
                "row_counts": {mode: len(rows) for mode, rows in datasets.items()},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("Final counts:")
    print(json.dumps(final_counts, indent=2))
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
