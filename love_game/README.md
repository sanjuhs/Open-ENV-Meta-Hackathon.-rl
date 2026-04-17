# Love Game

`love_game` is a small, intentionally playful training playground for tiny language models.

## Final Report

- [LOVE_GAME_DEEP_REPORT.md](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/reports/LOVE_GAME_DEEP_REPORT.md)
- [Report assets](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/reports/assets/20260418_2m_snapshot)

The idea is:

- define a fictional character
- generate synthetic conversations in that character's voice
- create datasets for multiple training styles
- compare what each training method teaches a very small model

This is not meant to be a production system or a deceptive impersonation tool.
It is a teaching/demo environment for:

- `SFT`
- `DPO`
- lightweight `RLHF`-style preference learning
- `GRPO` / verifier-style experiments

## What Is In Here

- [RAW_BIO.md](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/RAW_BIO.md)
  Raw notes copied from the prompt, lightly cleaned.
- [CHARACTER_PROFILE.md](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/CHARACTER_PROFILE.md)
  Refined fictional character profile with more detail.
- [TRAINING_METHODS.md](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/TRAINING_METHODS.md)
  Student-friendly guide to SFT, DPO, PPO, GRPO, and reward modeling.
- [character_profile.json](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/character_profile.json)
  Machine-readable character sheet used by the generators.
- [dataset_plan.md](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/dataset_plan.md)
  What datasets we generate and why.
- [generate_datasets.py](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/generate_datasets.py)
  Generates SFT, preference, and RL-style JSONL datasets with the OpenAI API.
- [expand_datasets.py](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/expand_datasets.py)
  Generates larger batches in parallel and merges them with deduplication.
- [prepare_training_sets.py](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/prepare_training_sets.py)
  Derives reward-model and PPO/GRPO-ready views from the base datasets.
- [dataset_viewer.py](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/dataset_viewer.py)
  Runs a local browser-based viewer/editor for the JSONL datasets.
- [train_reward_model.py](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/train_reward_model.py)
  Trains a tiny pure-Python reward model on the preference data.
- [DATASET_OVERVIEW.md](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/DATASET_OVERVIEW.md)
  Presentation-friendly explanation of what each dataset is for.
- [reward.py](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/reward.py)
  Starter rule-based reward heuristics for the environment.

## Character

The current fictional character is **Aditi**:

- 26-year-old woman
- graphic designer
- Bangalore-based
- high-energy, playful, impulsive, affectionate
- mostly English, with some Hinglish and a little Kannada mixing
- uses casual expletives at times
- emotionally expressive, quick to react, quick to recover

## Dataset Types

This folder is designed to generate three kinds of datasets:

1. `SFT`
   - input: conversation context + character profile
   - output: a single in-character reply

2. `DPO` / preference pairs
   - input: same scenario
   - output: one preferred response and one rejected response

3. `RL-style episodes`
   - input: state + message + candidate response
   - output: reward components and episode metadata

## Suggested Teaching Story

This folder works well for demonstrating:

- how to turn a messy persona idea into structured data
- how SFT examples differ from preference pairs
- how a reward function can only approximate warmth, care, or chemistry
- why partially verifiable conversational tasks are interesting

## Quick Start

Generate starter datasets:

```bash
python3 love_game/generate_datasets.py \
  --profile love_game/character_profile.json \
  --output-dir love_game/datasets \
  --model gpt-5.4-mini \
  --sft-count 24 \
  --dpo-count 18 \
  --rl-count 18

python3 love_game/prepare_training_sets.py

python3 love_game/dataset_viewer.py

python3 love_game/train_reward_model.py
```

This will create:

- `love_game/datasets/sft_train.jsonl`
- `love_game/datasets/dpo_train.jsonl`
- `love_game/datasets/rl_train.jsonl`
- `love_game/datasets/reward_model_train.jsonl`
- `love_game/datasets/rm_pointwise_train.jsonl`
- `love_game/datasets/rlhf_pairs_train.jsonl`
- `love_game/datasets/ppo_prompts.jsonl`
- `love_game/datasets/grpo_prompts.jsonl`
- `love_game/datasets/manifest.json`

Or use the wrapper:

```bash
./scripts/love-game.sh viewer
./scripts/love-game.sh generate-more --sft-count 120 --dpo-count 90 --rl-count 90
./scripts/love-game.sh train-rm
```

## Why This Exists

This is a deliberately small, fun experiment:

- tiny model
- fictional character
- synthetic data
- several training styles

It is designed to be understandable, fast to demo, and useful for explaining the strengths and limits of RL and preference learning.
