#!/usr/bin/env python3
"""Derive additional training-set formats from the base Love Game datasets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from love_game.common import DATASETS_DIR, dedupe_rows, read_jsonl, write_jsonl
from love_game.training_text import build_prompt_from_row


def main() -> None:
    sft_rows = read_jsonl(DATASETS_DIR / "sft_train.jsonl")
    dpo_rows = read_jsonl(DATASETS_DIR / "dpo_train.jsonl")
    rl_rows = read_jsonl(DATASETS_DIR / "rl_train.jsonl")

    reward_rows = []
    rm_pointwise_rows = []
    rlhf_rows = []
    for row in dpo_rows:
        preference_reason = row.get(
            "preference_reason",
            "Chosen is more in-character, more specific, warmer, or more emotionally appropriate than rejected.",
        )
        reward_rows.append(
            {
                "scenario_id": row["scenario_id"],
                "prompt": build_prompt_from_row(row),
                "chosen": row["chosen"],
                "rejected": row["rejected"],
                "label": 1,
                "preference_reason": preference_reason,
                "conversation": row.get("conversation", []),
            }
        )
        rm_pointwise_rows.append(
            {
                "scenario_id": row["scenario_id"],
                "prompt": build_prompt_from_row(row),
                "response": row["chosen"],
                "label": 1,
                "source": "chosen",
                "conversation": row.get("conversation", []),
            }
        )
        rm_pointwise_rows.append(
            {
                "scenario_id": row["scenario_id"],
                "prompt": build_prompt_from_row(row),
                "response": row["rejected"],
                "label": 0,
                "source": "rejected",
                "conversation": row.get("conversation", []),
            }
        )
        rlhf_rows.append(
            {
                "scenario_id": row["scenario_id"],
                "prompt": build_prompt_from_row(row),
                "preferred_response": row["chosen"],
                "dispreferred_response": row["rejected"],
                "preference_reason": preference_reason,
                "conversation": row.get("conversation", []),
            }
        )

    ppo_rows = []
    for row in sft_rows:
        ppo_rows.append(
            {
                "scenario_id": row["scenario_id"],
                "prompt": build_prompt_from_row(row),
                "reference_reply": row["assistant_reply"],
                "tags": row.get("tags", []),
                "conversation": row.get("conversation", []),
            }
        )

    grpo_rows = []
    for row in rl_rows:
        grpo_rows.append(
            {
                "scenario_id": row["scenario_id"],
                "prompt": build_prompt_from_row(row),
                "candidate_reply": row["candidate_reply"],
                "expected_goodness": row.get("expected_goodness"),
                "latent_state": row.get("latent_state", {}),
                "reward": row.get("reward", {}),
                "conversation": row.get("conversation", []),
            }
        )

    reward_rows = dedupe_rows(reward_rows)
    rm_pointwise_rows = dedupe_rows(rm_pointwise_rows)
    rlhf_rows = dedupe_rows(rlhf_rows)
    ppo_rows = dedupe_rows(ppo_rows)
    grpo_rows = dedupe_rows(grpo_rows)

    write_jsonl(DATASETS_DIR / "reward_model_train.jsonl", reward_rows)
    write_jsonl(DATASETS_DIR / "rm_pointwise_train.jsonl", rm_pointwise_rows)
    write_jsonl(DATASETS_DIR / "rlhf_pairs_train.jsonl", rlhf_rows)
    write_jsonl(DATASETS_DIR / "ppo_prompts.jsonl", ppo_rows)
    write_jsonl(DATASETS_DIR / "grpo_prompts.jsonl", grpo_rows)

    manifest = {
        "reward_model_train.jsonl": len(reward_rows),
        "rm_pointwise_train.jsonl": len(rm_pointwise_rows),
        "rlhf_pairs_train.jsonl": len(rlhf_rows),
        "ppo_prompts.jsonl": len(ppo_rows),
        "grpo_prompts.jsonl": len(grpo_rows),
    }
    (DATASETS_DIR / "derived_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    for name, count in manifest.items():
        print(f"Wrote {name} ({count} rows)")


if __name__ == "__main__":
    main()
