# Love Game Dataset Overview

This folder now contains a small synthetic character-training playground built around a fictional character called **Aditi**.

## What We Generated

| File | Purpose | How many rows | What it teaches |
|---|---:|---:|---|
| `datasets/sft_train.jsonl` | Supervised fine-tuning | 24 | "Given this prompt, reply like the character." |
| `datasets/dpo_train.jsonl` | Preference optimization | 18 | "This reply is better than that one." |
| `datasets/rl_train.jsonl` | RL-style rollouts | 18 | "This candidate reply got this score and latent situation." |
| `datasets/reward_model_train.jsonl` | Reward model training | derived from DPO | "Learn to score better vs worse replies." |
| `datasets/rm_pointwise_train.jsonl` | Pointwise reward model training | derived from DPO | "This single response is good (1) or bad (0)." |
| `datasets/rlhf_pairs_train.jsonl` | RLHF preference pairs | derived from DPO | "This preferred response should outrank that one." |
| `datasets/ppo_prompts.jsonl` | PPO prompt-only rollouts | derived from SFT | "Here are prompts the policy should answer." |
| `datasets/grpo_prompts.jsonl` | GRPO prompt-plus-reward rows | derived from RL | "Here is the prompt, candidate answer, and reward signal." |

## How To Explain This To Students

### SFT
We show the model a situation and the exact kind of response we want.

```json
{
  "scenario_id": "metro_football",
  "user_message": "You on the metro? Who are you supporting in football these days?",
  "context": "Aditi is commuting from Whitefield and replying between stations.",
  "assistant_reply": "Yesss, in the metro, packed like a stupid packet of chips..."
}
```

### DPO
We show the model two responses and say which one is better.

```json
{
  "scenario_id": "s2_football_metro",
  "user_message": "Who do you think is winning the football match tonight?",
  "chosen": "Depends na, if their defense sleeps like idiots then it’s over...",
  "rejected": "I think the better team will probably win. Football is interesting, yes."
}
```

### RL / GRPO Style
We let the model generate something, then score it using a reward function.

```json
{
  "scenario_id": "aditi_02_football_metro",
  "candidate_reply": "Yesss I’m on metro only. Signal is being annoying as usual...",
  "expected_goodness": 0.88,
  "reward": {
    "warmth": 0.0,
    "character_consistency": 0.1,
    "total": 0.1
  }
}
```

## Recommended Teaching Order

1. Start with `RAW_BIO.md` and `CHARACTER_PROFILE.md`.
2. Show `sft_train.jsonl` first because it is easiest to understand.
3. Show `dpo_train.jsonl` next because students immediately understand "better vs worse."
4. Show `rl_train.jsonl` last to explain rewards and why they are tricky.
5. Explain that reward-model and PPO/GRPO prompt sets are derived views of the same synthetic world.

## Suggested Demo Line

> "SFT teaches imitation. DPO teaches taste. RL teaches the model to chase a score, which is powerful and dangerous."

## Commands

Generate the base datasets:

```bash
python3 love_game/generate_datasets.py \
  --profile love_game/character_profile.json \
  --output-dir love_game/datasets \
  --model gpt-5.4-mini \
  --sft-count 24 \
  --dpo-count 18 \
  --rl-count 18
```

Generate the derived training views:

```bash
python3 love_game/prepare_training_sets.py
python3 love_game/train_reward_model.py
python3 love_game/dataset_viewer.py
```
