#!/usr/bin/env python3
"""Generate synthetic SFT, DPO, and RL-style datasets for Love Game."""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from love_game.reward import compact_text, score_reply

SCENARIO_SEEDS = [
    "You had a bad day at work and message her late at night.",
    "You forgot to reply for a few hours and now want to repair the vibe.",
    "You ask her to go for an ice cream walk after work.",
    "You are nervous about something and want reassurance.",
    "You say something mildly stupid and she teases you back.",
    "You ask her about football while she is commuting in the metro.",
    "You ask if she is free this weekend for a Bangalore plan.",
    "You are low-energy and she is trying to pull you out of it.",
    "You had a fight and want to reconnect without overexplaining.",
    "You ask her what she wants for dinner after the gym.",
    "You are overthinking the relationship and want clarity.",
    "You ask about her MBA plans and whether work is burning her out.",
]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        type=Path,
        default=ROOT / "love_game" / "character_profile.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "love_game" / "datasets",
    )
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--sft-count", type=int, default=24)
    parser.add_argument("--dpo-count", type=int, default=18)
    parser.add_argument("--rl-count", type=int, default=18)
    parser.add_argument("--sft-batch-size", type=int, default=8)
    parser.add_argument("--dpo-batch-size", type=int, default=6)
    parser.add_argument("--rl-batch-size", type=int, default=6)
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    return parser


def load_api_key(env_name: str) -> str:
    key = os.getenv(env_name, "")
    if key:
        return key

    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{env_name}="):
                value = line.split("=", 1)[1].strip().strip('"')
                if value:
                    return value
    raise RuntimeError(f"Missing API key in {env_name} and .env")


def post_responses(
    api_key: str,
    model: str,
    prompt: str,
    *,
    max_output_tokens: int | None = 3000,
    timeout_seconds: int = 300,
    json_schema: dict | None = None,
) -> str:
    payload = {
        "model": model,
        "input": prompt,
        "temperature": 0.9,
    }
    if max_output_tokens is not None:
        payload["max_output_tokens"] = max_output_tokens
    if json_schema is not None:
        payload["text"] = {
            "format": {
                "type": "json_schema",
                "name": json_schema["name"],
                "schema": json_schema["schema"],
                "strict": True,
            }
        }
    result = subprocess.run(
        [
            "curl",
            "-sS",
            "--max-time",
            str(timeout_seconds),
            "https://api.openai.com/v1/responses",
            "-H",
            f"Authorization: Bearer {api_key}",
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps(payload),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    body = json.loads(result.stdout)
    if body.get("output_text"):
        return body["output_text"]
    parts = []
    for item in body.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if text:
                parts.append(text)
    return "\n".join(parts)


def build_prompt(profile: dict, mode: str, count: int, seeds: list[str]) -> str:
    seed_lines = "\n".join(f"- {seed}" for seed in seeds)
    profile_json = json.dumps(profile, indent=2)
    if mode == "sft":
        return f"""
You are generating synthetic training data for a tiny model roleplay experiment.

Character profile:
{profile_json}

Generate {count} JSON objects for supervised fine-tuning.
Each object must have:
- scenario_id
- user_message
- context
- assistant_reply
- tags

Requirements:
- replies should sound like this fictional Aditi character
- mostly English
- occasional Hinglish or light Kannada mixing
- sometimes uses words like "fuck" naturally, but not in every reply
- playful, specific, modern Bangalore energy
- no safety disclaimers, no mention of being an AI
- keep replies under 120 words

Use these scenario seeds for inspiration:
{seed_lines}

Return ONLY valid JSON as an array.
""".strip()
    if mode == "dpo":
        return f"""
You are generating preference-training data for a tiny fictional character model.

Character profile:
{profile_json}

Generate {count} JSON objects for DPO.
Each object must have:
- scenario_id
- user_message
- context
- chosen
- rejected
- preference_reason

Requirements:
- chosen should be clearly more in-character, warmer, more specific, or more emotionally appropriate
- rejected should be bland, off-tone, slightly robotic, too generic, too cold, or factually off
- keep both replies under 120 words

Use these scenario seeds for inspiration:
{seed_lines}

Return ONLY valid JSON as an array.
""".strip()
    return f"""
You are generating RL-style conversational data for a tiny fictional character model.

Character profile:
{profile_json}

Generate {count} JSON objects.
Each object must have:
- scenario_id
- user_message
- context
- candidate_reply
- latent_state
- expected_goodness
- notes

The candidate_reply should be plausible, but not always perfect.
We will score it later with a separate reward function.

Use these scenario seeds for inspiration:
{seed_lines}

Return ONLY valid JSON as an array.
""".strip()


def parse_json_array(text: str) -> list[dict]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0]
    return json.loads(cleaned)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def enrich_rl_rows(rows: list[dict]) -> list[dict]:
    enriched = []
    for row in rows:
        reply = compact_text(row.get("candidate_reply", ""))
        reward = score_reply(reply).to_dict()
        enriched.append({**row, "candidate_reply": reply, "reward": reward})
    return enriched


def generate_rows(
    *,
    api_key: str,
    model: str,
    profile: dict,
    mode: str,
    total_count: int,
    batch_size: int,
    seeds: list[str],
) -> list[dict]:
    rows: list[dict] = []
    while len(rows) < total_count:
        requested = min(batch_size, total_count - len(rows))
        prompt = build_prompt(profile, mode, requested, seeds[: min(len(seeds), 10)])
        raw = post_responses(api_key=api_key, model=model, prompt=prompt)
        batch = parse_json_array(raw)
        rows.extend(batch[:requested])
        print(
            f"Generated {mode} batch: requested={requested}, "
            f"received={len(batch)}, total={len(rows)}/{total_count}"
        )
    return rows[:total_count]


def main() -> None:
    args = build_arg_parser().parse_args()
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    api_key = load_api_key(args.api_key_env)

    rng = random.Random(42)
    seeds = SCENARIO_SEEDS[:]
    rng.shuffle(seeds)

    outputs: dict[str, Path] = {}
    manifest: dict[str, dict] = {}

    batch_sizes = {
        "sft": args.sft_batch_size,
        "dpo": args.dpo_batch_size,
        "rl": args.rl_batch_size,
    }

    for mode, count in (("sft", args.sft_count), ("dpo", args.dpo_count), ("rl", args.rl_count)):
        rows = generate_rows(
            api_key=api_key,
            model=args.model,
            profile=profile,
            mode=mode,
            total_count=count,
            batch_size=batch_sizes[mode],
            seeds=seeds,
        )
        if mode == "rl":
            rows = enrich_rl_rows(rows)
        output_path = args.output_dir / f"{mode}_train.jsonl"
        write_jsonl(output_path, rows)
        outputs[mode] = output_path
        manifest[mode] = {
            "count": len(rows),
            "path": str(output_path),
            "model": args.model,
        }
        print(f"Wrote {output_path} ({len(rows)} rows)")

    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()
