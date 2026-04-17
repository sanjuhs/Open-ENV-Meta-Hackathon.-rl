# Training Methods For Love Game

This file explains the main training styles we can demonstrate using the fictional Aditi character.

## Summary Table

| Method | What data it needs | What the model learns | Why it is useful here | Difficulty tonight |
|---|---|---|---|---|
| `SFT` | prompt -> good reply | imitate the character voice directly | fastest way to get something working | low |
| `DPO` | prompt + chosen reply + rejected reply | prefer better replies over worse ones | great for style, warmth, and tone | medium |
| `Reward Modeling` | prompt + reply + scalar or pairwise score | predict which replies are better | useful before RLHF/PPO-style training | medium |
| `PPO` | prompt + generated reply + reward model | optimize toward learned reward | classic RLHF pipeline | high |
| `GRPO` | prompt + generated replies + programmatic reward | optimize using grouped reward comparisons | good when reward is partly rule-based | medium-high |
| `Rule-based RL` | prompt + generated reply + hand-coded reward | optimize for simple signals | good for teaching what reward can and cannot capture | medium |

## Recommended Order

If this is for a student demo, the best order is:

1. `SFT`
2. `DPO`
3. optional `GRPO` or reward-based RL

Why:
- SFT is easiest to understand
- DPO shows the power of preferences
- RL shows where reward engineering becomes tricky

## 1. SFT

### Data shape

```json
{
  "system": "You are Aditi...",
  "user": "I had a bad day.",
  "assistant": "Fuck, that sounds exhausting. Do you want to vent or do you want distraction?"
}
```

### What it teaches

- persona consistency
- word choice
- pacing
- emotional style

### Weakness

It only learns to imitate examples. It does not understand "better vs worse" beyond what is implicit.

## 2. DPO

### Data shape

```json
{
  "prompt": "I had a bad day.",
  "chosen": "Fuck, that sounds exhausting. Do you want to vent or do you want distraction?",
  "rejected": "Okay. You should just sleep early."
}
```

### What it teaches

- which response style is preferable
- emotional appropriateness
- tone ranking

### Why it is a great fit here

Because conversational quality is often easier to express as:
- this one is better
- that one is worse

rather than as a single numeric score.

## 3. Reward Modeling

### Data shape

Either pairwise:

```json
{
  "prompt": "...",
  "reply_a": "...",
  "reply_b": "...",
  "preferred": "a"
}
```

or scalar:

```json
{
  "prompt": "...",
  "reply": "...",
  "score": 0.82
}
```

### What it teaches

A separate model learns to score replies.

Then RL can optimize against that score.

## 4. PPO

Classic RLHF pipeline:

1. SFT model
2. reward model
3. PPO optimization

### Why it is harder tonight

- more moving pieces
- less stable
- harder to explain quickly

## 5. GRPO

GRPO is useful when:
- you can define grouped rewards
- you want simpler RL than a full PPO setup

In Love Game, GRPO could optimize for:
- fact consistency
- tone consistency
- warmth score
- non-genericity
- not being emotionally dismissive

## What I would show students

The clearest teaching path is:

1. show SFT examples
2. show DPO pairs
3. show a simple reward function
4. explain why some things are only partially verifiable
