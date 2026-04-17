# DocEdit Qwen2.5-3B Checkpoints

This repository contains the checkpoint artifacts for a DocEdit Game experiment built on top of:

- base model: `Qwen/Qwen2.5-3B-Instruct`
- hardware: `1x H200 SXM`
- training recipe: `SFT -> GRPO`
- date: `April 17, 2026`

Primary Hub repo:
- [sanjuhs/docedit-qwen25-3b-checkpoints](https://huggingface.co/sanjuhs/docedit-qwen25-3b-checkpoints)

---

## What This Repository Is

This repo stores the checkpoints, metrics, and supporting notes for a narrow structured document-repair experiment.

The task is:
- read a corrupted Word-style structured document
- read an edit instruction
- repair the intended corruptions
- preserve the rest of the document
- minimize collateral damage

This is a **research/demo repo**, not a production release.

---

## Base Model

- `Qwen/Qwen2.5-3B-Instruct`

We chose this model because it is:
- small enough to fine-tune quickly on a single H200
- large enough to show meaningful task adaptation
- practical for LoRA-based experimentation

---

## Training Setup

We used a two-stage setup:

1. **SFT**
   - supervised fine-tuning on paired corrupted -> repaired document examples
   - implemented as a LoRA adapter

2. **GRPO**
   - reinforcement learning from the DocEdit verifier reward
   - continued from the SFT LoRA adapter
   - still LoRA-based, not full-model fine-tuning

Important note:

This run is a **rewrite-policy baseline**:
- the model outputs a repaired document
- it does not yet implement the final frontier-planner -> applicator architecture we discussed later

That means this repo should be interpreted as:
- a strong small-model baseline artifact
- a checkpoint series we can compare against future tool-policy work

---

## What Is In This Repo

### `qwen25_3b_sft/`

LoRA adapter after supervised fine-tuning.

This stage teaches:
- document format discipline
- markup preservation
- the basic corrupted -> repaired mapping

### `qwen25_3b_grpo/`

LoRA adapter after GRPO, plus intermediate checkpoints.

This stage optimizes for:
- verifier reward
- similarity improvement
- reduced collateral damage
- output-format obedience

### `metrics/`

This folder contains:
- smoke eval outputs
- presentation-oriented metrics summaries

### `docs/`

This folder contains explanatory notes and walkthrough material used to present the project.

---

## Training Data

The training data was generated from the DocEdit benchmark pipeline.

Each task includes:
- `doc_seed`
- `corruption_seed`
- `difficulty`
- `domain`
- a corrupted source document
- a target repaired document
- corruption metadata

Domains include:
- legal
- pharmaceutical

Corruptions include:
- spelling
- casing
- punctuation
- content deletion/insertion
- formatting loss
- PDF artifact cleanup
- junk character cleanup

---

## SFT Summary

### Purpose

Teach the model the core repair pattern before RL.

### Result

- hardware: `1x H200`
- runtime: about `109.38s`
- final train loss: about `0.06346`
- final mean token accuracy: about `0.98954`

### Artifact

- LoRA adapter size: about `119.8 MB`

---

## GRPO Summary

### Purpose

Use the game verifier as a reward signal and continue training from the SFT adapter.

### Result

- runtime: about `5562.75s`
- total steps: `100`
- final logged train loss: about `0.03506`
- final logged reward at step `100`: about `0.79567`

Intermediate checkpoints written:
- `checkpoint-25`
- `checkpoint-50`
- `checkpoint-75`
- `checkpoint-100`

Final GRPO adapter artifact:
- `adapter_model.safetensors` about `239.5 MB`

### Important interpretation

GRPO showed that the RL loop works end-to-end on the H200 and produces a complete adapter plus checkpoint trail.

This does **not** by itself prove that the rewrite-policy model is the best final product design.

Instead, it gives us:
- a trained small-model RL baseline
- a concrete artifact to compare against frontier-model tool use
- a launch point for future tool-policy or planner/executor designs

---

## Current Evaluation Artifacts

The repo includes small smoke evaluation outputs for:

- base `Qwen2.5-3B-Instruct`
- SFT LoRA adapter

At the time of upload, these smoke evals are intentionally small and should be treated as sanity checks, not final benchmark conclusions.

The purpose is to show:
- that the checkpoints load
- that the evaluation path works
- that future comparisons can be made reproducibly

---

## What The Model Currently Does

Current behavior:
- takes a corrupted structured document plus instruction
- outputs a repaired document directly

This is useful for:
- baseline benchmarking
- fast experimentation
- demonstrating that a small model can learn the task format

This is **not yet** the final “frontier planner + applicator executor” system.

---

## Why This Repo Still Matters

Even though our later design discussion moved toward a more structured frontier-planner -> applicator setup, this repo remains useful because it captures:

1. a reproducible small-model baseline
2. a completed H200 SFT run
3. a completed H200 GRPO run
4. concrete weights, metrics, and checkpoints
5. a reference point for future tool-policy work

In other words:

This repo answers the question:

> Can a small open model be adapted and RL-tuned on this document repair task at all?

The answer is yes.

---

## Known Limitations

This repo has several important limitations:

1. The current policy is a **rewrite policy**, not a tool-call policy.
2. The evaluation uploaded here is still mostly smoke-level, not final large-scale benchmarking.
3. The architecture is evolving toward a cleaner frontier-planner -> applicator design.
4. The current run used the existing reward and data scaffolding; future versions may use a better patch language or tool trajectory format.

---

## Recommended Next Step

The next research step is not “train a bigger rewrite model.”

The better next step is:

1. let a frontier model such as `GPT-5.4` drive a structured edit or tool language directly
2. collect those successful traces
3. compare cost and quality against this rewrite-policy baseline
4. decide whether to train a smaller applicator model from those traces

That makes this repo a baseline artifact for future comparison.

---

## Files You May Want To Inspect

- `qwen25_3b_sft/`
- `qwen25_3b_grpo/`
- `metrics/presentation_metrics.json`
- `metrics/qwen25_3b_base_smoke.jsonl`
- `metrics/qwen25_3b_sft_smoke.jsonl`
- `docs/DOCEDIT_STUDENT_WALKTHROUGH.md`

---

## Usage Note

These checkpoints are intended for:
- experimentation
- evaluation
- presentation/demo purposes

They should not be treated as production-ready legal or pharmaceutical editing systems without a much more complete evaluation program.
