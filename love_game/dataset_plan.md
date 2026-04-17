# Love Game Dataset Plan

We want to generate synthetic datasets for multiple training styles from the same fictional character profile.

## SFT Dataset

Purpose:
- teach the model how Aditi talks

Each row:
- character profile summary
- scenario
- optional conversation history
- good in-character reply

## DPO Dataset

Purpose:
- teach the model which replies are better

Each row:
- scenario
- chosen reply
- rejected reply
- short explanation for why the chosen one is better

## RL-Style Dataset

Purpose:
- create episodes with rewards

Each row:
- scenario
- current emotional state
- candidate reply
- reward components:
  - warmth
  - consistency
  - playfulness
  - supportiveness
  - contradiction penalty
  - blandness penalty

## Why this is useful for the talk

It lets us show:
- what imitation looks like
- what preference learning looks like
- what reward-driven learning looks like

using the exact same fictional character.
