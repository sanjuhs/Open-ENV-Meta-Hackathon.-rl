# Love Game Training Method Matrix

This is the clean mapping between training methods and the datasets in `love_game`.

## What We Have Right Now

| Method | Dataset | What it contains | Status |
|---|---|---|---|
| `SFT` | `datasets/sft_train.jsonl` | prompt/context -> target reply | ready |
| `DPO` | `datasets/dpo_train.jsonl` | chosen vs rejected reply pairs | ready |
| `RLHF pairs` | `datasets/rlhf_pairs_train.jsonl` | prompt + preferred/dispreferred responses | ready |
| `Reward model` | `datasets/rm_pointwise_train.jsonl` | prompt + response + label `1/0` | ready |
| `Reward model (pairwise)` | `datasets/reward_model_train.jsonl` | prompt + chosen + rejected | ready |
| `PPO prompts` | `datasets/ppo_prompts.jsonl` | prompt-only rollout prompts, with reference reply | ready |
| `GRPO prompts` | `datasets/grpo_prompts.jsonl` | prompt + candidate reply + reward metadata | ready |
| `Rule-based reward` | `reward.py` | heuristic scorer | ready |

## How Each Method Works

### 1. SFT

Use:
- `sft_train.jsonl`

Goal:
- teach the model to imitate good target responses

Best for:
- first-stage alignment
- low-risk warm start

### 2. DPO

Use:
- `dpo_train.jsonl`
or
- `rlhf_pairs_train.jsonl`

Goal:
- teach the model which response is preferred without training a separate reward model first

Best for:
- style preference
- tone shaping
- "this answer is better than that one"

### 3. Reward Model

Use:
- `rm_pointwise_train.jsonl`
or
- `reward_model_train.jsonl`

Goal:
- train a scorer that predicts whether a response is good or bad

Best for:
- later PPO
- later ranking
- demoing how reward models work

### 4. PPO

Use:
- prompts from `ppo_prompts.jsonl`
- reward from:
  - learned reward model
  - rule-based reward function
  - or both combined

Goal:
- sample model outputs and optimize them against a reward signal

Needs:
- a policy model
- a reward model or reward function
- rollout loop

### 5. GRPO

Use:
- prompts from `grpo_prompts.jsonl`
- reward from:
  - `reward.py`
  - or a learned reward model

Goal:
- generate several candidate responses and optimize comparatively within a group

Best for:
- small-scale RL experiments when we can score outputs automatically

## What We Still Need For A More Convincing Run

The current data is enough to prove the pipeline works, but not enough to make a `135M` model feel strong.

Recommended next scales:

- `SFT`: at least `0.5M` to `2M` tokens
- `DPO / RLHF pairs`: at least `0.3M` to `1M` tokens
- `PPO / GRPO prompts`: at least a few thousand prompts

## Honest Take

For this project:

- `SFT -> DPO` is the most useful immediate path
- `Reward model -> PPO` is more complex, but very teachable
- `GRPO` is good if we trust the reward signal enough

The safest progression is:

1. scale SFT data
2. scale DPO data
3. train a better reward model
4. run PPO or GRPO on top
