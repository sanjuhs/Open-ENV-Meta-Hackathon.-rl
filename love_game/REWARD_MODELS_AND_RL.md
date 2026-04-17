# Reward Models, PPO, GRPO, RLHF, RLVR

## Short Version

Not every post-SFT method needs the same machinery.

| Method | Needs reward model? | Needs online rollouts? | What it optimizes against |
|---|---|---:|---|
| `SFT` | No | No | target completion |
| `DPO` | No | No | chosen vs rejected preferences |
| `PPO` | Usually yes | Yes | scalar reward |
| `GRPO` | Sometimes | Yes | grouped reward comparisons |
| `RLHF` | Usually yes | Usually yes | learned human preference signal |
| `RLVR` | No | Yes | verifiable programmatic reward |
| `Constitutional AI` | Not necessarily | Optional | critique/revision or AI feedback |

## What Is Usually Used As A Reward Model?

The most standard reward model is:

- a **transformer encoder or decoder**
- with a **single scalar score head**
- trained on **chosen / rejected** human preference pairs

That is the classic RLHF reward model.

Two common patterns:

### 1. Classical reward model

- input: `prompt + response`
- output: one scalar reward
- training data: pairwise preferences or pointwise labels

This is the most common thing people mean by “reward model.”

### 2. Process reward model

- input: a reasoning trace or step
- output: a score for that intermediate step

This is more common in reasoning / math / tool-use settings.

## What We Have In Love Game Right Now

### Already real

- `SFT`
- `DPO`
- a tiny toy reward model

### Added now

- a **real neural reward-model trainer**:
  - [run_reward_model_transformer.py](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/run_reward_model_transformer.py)

This trains:

- `prompt + response`
- binary label `good / bad`
- using a transformer classification head

So this is the first practical “real reward model” path in the repo.

## What Model Should We Use For The Reward Model?

For a practical small reward model, I would use:

- `distilroberta-base`
- or `distilbert-base-uncased`
- or a small modern encoder if you want to swap later

Why:

- fast
- stable
- good enough for pairwise / pointwise preference scoring
- much cheaper than using a full LLM as the reward model

For the tiny Love Game setup, this is much more reasonable than asking another large generative model to be the scorer during every training step.

## Can We Use A Tiny LLM As The Reward Model?

Yes, but there are two different meanings.

### 1. Tiny classifier model

Best practical option.

- efficient
- easy to train
- good for PPO
- good for offline evaluation

### 2. Tiny generative judge model

Possible, but less clean.

- slower
- harder to calibrate
- harder to use as a scalar reward

For this project, I recommend a **classifier reward model**, not a tiny generative judge.

## Can We Use Constitutional AI?

Yes, but it solves a different problem.

Constitutional AI usually means:

1. define principles or a constitution
2. let a model critique / revise outputs against those principles
3. possibly use that AI feedback to generate preference data

That can help us:

- generate better `chosen / rejected` pairs
- generate critique data
- bootstrap a cleaner reward model

But constitutional AI is **not itself a reward model**.

For Love Game, the cleanest use would be:

- use constitutional-style principles to synthesize or critique responses
- then train a reward model from those judgments

## How PPO Would Work Here

PPO usually needs:

1. a policy model
2. prompt dataset
3. reward model or reward function
4. online sampling

Love Game mapping:

- policy model: `SmolLM2-135M-Instruct` fine-tuned checkpoint
- prompts: `ppo_prompts.jsonl`
- reward:
  - neural reward model
  - or rule-based reward
- rollout training: not yet implemented in repo

## How GRPO Would Work Here

GRPO usually needs:

1. prompt dataset
2. current policy model
3. multiple sampled responses per prompt
4. reward function or reward model
5. grouped comparison update

Love Game mapping:

- prompts: `grpo_prompts.jsonl` or prompt-only rollouts
- scorer:
  - rule-based reward in [reward.py](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/reward.py)
  - or neural reward model

GRPO is especially nice when:

- you already have a programmatic verifier
- or a relatively cheap reward function

## RLHF vs RLVR

### RLHF

Uses human or learned human preference signals.

Best when:

- the task is subjective
- “good” is taste-based
- you need human-like warmth or tone

Love Game is mostly in this category.

### RLVR

Uses verifiable rewards.

Best when:

- the answer can be checked automatically
- math, code, tools, exact formatting, etc.

Love Game is **not strongly RLVR** unless we reduce it to narrow measurable proxies.

So the honest answer is:

- Love Game is mostly **RLHF / preference learning**
- not a pure RLVR task

## Best Order To Build This Properly

1. scale `SFT`
2. scale `DPO / RLHF pairs`
3. train neural reward model
4. run DPO again on the larger corpus
5. implement PPO or GRPO
6. compare:
   - base
   - SFT
   - DPO
   - PPO/GRPO

## If We Want To Be Practical On The H200

The best next GPU-heavy steps are:

1. train the neural reward model
2. evaluate reward-model accuracy
3. decide:
   - PPO with learned reward
   - or GRPO with learned reward / rule reward

For this repo, I would choose:

- **DPO first**
- then **neural reward model**
- then **GRPO**

before spending time on PPO.

Why:

- DPO already works
- reward model makes the RL story real
- GRPO is simpler to justify with grouped reward and small-model experiments

