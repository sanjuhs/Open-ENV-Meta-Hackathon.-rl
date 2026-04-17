# DocEdit Qwen2.5-3B Checkpoints

This repository stores checkpoint artifacts for the DocEdit Game experiments built on top of:

- base model: `Qwen/Qwen2.5-3B-Instruct`
- task: structured document repair
- setup: `SFT -> GRPO`

## What Is In This Repo

This repo is intended to keep all related weights in one place:

- `qwen25_3b_sft/`
  - LoRA adapter after supervised fine-tuning
- `qwen25_3b_grpo/`
  - GRPO checkpoints and final adapter after verifier-based RL
- `metrics/`
  - smoke eval outputs and short summaries

## What The Model Does

The model reads:
- an editing instruction
- a corrupted Word-style structured document

And returns:
- the repaired document markup

The model is trained to:
- fix the intended corruptions
- preserve valid formatting and structure
- minimize collateral damage

## Training Snapshot

### SFT

- hardware: `1x H200`
- adapter style: `LoRA`
- training runtime: about `109s`
- final train loss: about `0.0635`
- final mean token accuracy: about `0.9895`

### GRPO

GRPO continues from the SFT adapter and optimizes against the DocEdit verifier reward:
- structural correctness
- edit accuracy
- collateral damage penalty
- format obedience

## Important Note

These are research/demo checkpoints for a narrow structured document editing task. They should be evaluated on held-out benchmark cases before any production use.
