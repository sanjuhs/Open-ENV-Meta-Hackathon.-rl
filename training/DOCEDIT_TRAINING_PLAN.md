# DocEdit Training Plan

## Goal

Ship a convincing demo on top of `doc_edit_game_v2` with:

1. a preserved classic UI and a modern editor UI,
2. dual-seed reproducibility for document generation and corruption generation,
3. a frozen benchmark split and unified evaluation harness,
4. a strong proprietary baseline with `GPT-5.4`,
5. a small open model baseline served through a fast inference engine,
6. a warm-start supervised fine-tune (SFT),
7. a short-but-real GRPO / RLVR run overnight.

This document is written for the exact setup you described: a RunPod Secure Cloud Pod, likely using an `H200`, on-demand, with a large network volume and a 4-10 hour working window.

---

## Executive Recommendation

### Live RunPod note (April 17, 2026)

We validated this on a live `H200` pod started from the `vLLM Latest` template.

Observed behavior:

- the default template launched `Qwen/Qwen3-8B`,
- it started with `--gpu-memory-utilization 0.95`,
- it reserved roughly `137 GB / 143 GB` of GPU memory on the H200 even while idle,
- it served with only `--max-model-len 8128`,
- it blocked sidecar vLLM launches and local training on the same GPU.

Practical conclusion:

- the `vLLM Latest` template is acceptable for a dedicated inference pod,
- it is **not** the right template for mixed `SFT + GRPO + eval` work on a single GPU,
- for training, prefer a `PyTorch` template or a pod/container whose primary process is not already monopolizing the GPU,
- if you keep the current vLLM template, treat it as an inference-only pod unless you are willing to restart it with a different startup command.

### Hardware

Use:

- `H200 141GB` if available
- otherwise `H100 80GB`
- `Secure Cloud`
- `on-demand`
- `300GB-600GB` network volume

The `H200` is an excellent choice here because the extra memory gives us:

- more room for model weights + vLLM + trainer state,
- easier experimentation with 3B-class and 7B-class QLoRA runs,
- fewer last-minute OOM failures,
- more headroom for long contexts, larger batch sizes, and concurrent eval.

### RunPod template choice

Use the **PyTorch / Python 3.11 template**, not the `vLLM latest` template.

Reason:

- we need a mixed workload, not just serving,
- we need to install training libraries such as TRL / PEFT / Accelerate,
- we may run vLLM as a service or sidecar inside the same machine,
- the PyTorch template is the safer base when we need both training and inference on one node.

Recommended pattern:

1. start from RunPod `PyTorch` template,
2. install `vllm` inside that environment,
3. run vLLM only for fast inference / rollout generation,
4. run SFT and GRPO from the same base environment.

### Volume recommendation

Your planned `600GB` network volume is more than enough and is a safe choice.

That comfortably covers:

- the repo and artifacts,
- Hugging Face cache,
- vLLM model cache,
- training checkpoints,
- adapter checkpoints,
- eval manifests and JSONL logs,
- temporary copied datasets.

For a 4-10 hour sprint the volume cost is negligible relative to GPU cost, so if 600GB is already created, keep it.

---

## Why SFT First, Then GRPO

For this environment, the right stack is:

1. **SFT warm start**
2. **GRPO on top of that**

This is better than cold-start GRPO because:

- the policy starts with a basic understanding of the markup format,
- the model learns how to preserve structure before reward optimization,
- RL time is spent improving edit strategy rather than learning syntax from scratch,
- the verifier signal becomes more useful when the policy is already capable.

In practice, SFT reduces:

- reward hacking,
- format collapse,
- output drift,
- useless exploration,
- no-op or destructive actions.

---

## Why This Is RLVR, Not Classic RLHF

DocEdit is naturally an **RLVR** problem: reinforcement learning from a **verifiable reward**.

The environment already gives us:

- an exact target document,
- a structured corruption process,
- a similarity function,
- a collateral damage function,
- a corruption-aware edit accuracy function,
- a completion condition.

This means we do **not** need a learned reward model to get started.

That is a major advantage.

### Terminology

- **SFT**: supervised fine-tuning on demonstrations
- **DPO / preference optimization**: train from pairs of better/worse outputs
- **RLHF**: reinforcement learning from human or learned preference signals
- **RLVR**: reinforcement learning from deterministic or programmatically verified reward
- **GRPO**: a grouped relative policy optimization method that works well for verifiable tasks

For this project:

- primary path: `SFT -> GRPO`
- optional later path: add DPO if we generate ranked candidates
- avoid spending time on classical RLHF tonight

---

## Model Strategy

## Model families

We need three comparison tracks:

1. `GPT-5.4` baseline
2. small open base model baseline
3. fine-tuned version of that same small model

This gives a clean story:

- `GPT-5.4` is the strong upper reference
- the small base model shows the untuned floor
- SFT + GRPO shows the delta from training

## Initial model size

For an overnight first run, the best practical range is:

- safe: `0.5B-1.5B`
- ambitious but still manageable: `3B`
- risky for tonight: `7B`

If the goal is **“show uplift by tomorrow”**, start with:

- one `1B-3B` instruct model
- QLoRA for SFT
- QLoRA-compatible GRPO if supported in the chosen stack

---

## Training Modes We Can Support

There are two policy styles in this environment.

### A. Direct rewrite policy

The model sees:

- source document
- instruction
- metadata

It outputs:

- a fully edited document

Pros:

- simple
- easy to benchmark against GPT-5.4
- fewer moving parts

Cons:

- easy to damage markup
- hard to get precise local edits
- higher chance of over-editing

### B. Tool policy

The model sees:

- current document or chunk
- instruction
- observation metadata

It outputs:

- one tool call with params

Pros:

- explicit action space
- cleaner credit assignment
- naturally aligned with GRPO and RLVR
- easier to inspect and debug

Cons:

- more infra work
- requires sequential environment rollouts

### Recommendation

For the benchmark:

- support **direct rewrite** for GPT-5.4 and first local baselines

For RL:

- prefer **tool policy** if we can scaffold it quickly
- otherwise do a **direct rewrite GRPO prototype** tonight, then migrate to tool policy next

---

## Dataset Design

## SFT dataset

SFT requires explicit demonstrations.

We have two good ways to build them.

### Option 1. Direct rewrite SFT

Each example looks like:

```json
{
  "task_id": "d123_c456_L3",
  "mode": "direct_rewrite",
  "doc_seed": 123,
  "corruption_seed": 456,
  "difficulty": 3,
  "domain": "legal",
  "doc_type": "legal_contract",
  "instruction": "Fix 2 spelling errors ...",
  "source_document": "<heading ...> ...",
  "target_document": "<heading ...> ...",
  "messages": [
    {"role": "system", "content": "You are an expert document repair model..."},
    {"role": "user", "content": "Repair the following structured document..."},
    {"role": "assistant", "content": "<heading ...> fully corrected target ..."}
  ]
}
```

This is the easiest SFT warm start.

### Option 2. Tool trajectory SFT

Each example is a multi-step demonstration:

```json
{
  "task_id": "d123_c456_L3",
  "mode": "tool_policy",
  "instruction": "Fix 2 spelling errors ...",
  "steps": [
    {
      "observation": {
        "document_chunk": "...",
        "chunk_index": 0,
        "total_chunks": 2,
        "similarity": 0.91,
        "collateral_damage": 0.0
      },
      "assistant_action": {
        "tool": "replace",
        "params": {"target": "recieve", "content": "receive"}
      }
    },
    {
      "observation": {
        "document_chunk": "...",
        "chunk_index": 0,
        "total_chunks": 2,
        "similarity": 0.95,
        "collateral_damage": 0.0
      },
      "assistant_action": {
        "tool": "replace",
        "params": {"target": "Advsere", "content": "Adverse"}
      }
    }
  ]
}
```

This is more aligned with GRPO, but harder to generate.

### Best SFT warm start tonight

Use **direct rewrite SFT** first.

Why:

- we already have source and target,
- no teacher trace generation is required,
- we can create many examples immediately,
- it is enough to teach the model markup preservation and task shape.

---

## GRPO dataset

GRPO is not a static supervised dataset in the same sense.

It needs:

- a prompt distribution,
- an environment/verifier,
- a reward function,
- a rollout mechanism.

So the “GRPO dataset” is really a **task manifest** plus runtime sampling.

Each GRPO item should minimally contain:

```json
{
  "task_id": "d123_c456_L3",
  "doc_seed": 123,
  "corruption_seed": 456,
  "difficulty": 3,
  "domain": "legal",
  "doc_type": "legal_contract",
  "instruction": "Fix 2 spelling errors ..."
}
```

At rollout time we generate or load:

- source document
- target document
- current observation
- reward after each action or final output

### GRPO input distribution

For tonight’s run:

- focus on low and medium difficulty first
- exclude the most pathological artifact-heavy tasks until the policy is stable

Suggested first GRPO training distribution:

- domain: `legal`, `pharma`, `business`
- difficulty: `1`, `2`, `3`
- max steps: existing environment defaults

Later curriculum:

- add difficulty `4`
- then `5`
- then `6`

---

## Reward Design Review

The current reward components are already good enough to start.

### Existing environment reward

From the environment logic, the main structure is:

```text
reward =
  similarity_after - similarity_before
  - 0.01 if the action fails
  - 0.02 * collateral_damage
  - 0.002 for navigation-only actions
  + completion bonus if similarity >= 0.999
```

### Existing final grading

Final score uses:

- `similarity`
- `edit_accuracy`
- `collateral_damage`

Composite score:

```text
0.50 * similarity
+ 0.25 * edit_accuracy
+ 0.25 * (1 - collateral_damage)
```

### Is this reward good enough?

Yes, for a first RLVR / GRPO run.

It is already:

- grounded in the exact target,
- sensitive to incremental improvement,
- punitive toward collateral damage,
- incentivized toward completion.

### What should we watch for?

Potential failure modes:

1. **rewrite everything** behavior
2. **format collapse**
3. **reward hacking through near-target copying**
4. **tool spam**
5. **navigation abuse**

### Recommended reward monitoring

Track these during GRPO:

- mean incremental reward
- final similarity
- final composite score
- edit accuracy
- collateral damage
- steps used
- percentage of noop / failed actions
- exact match rate

Also track:

- reward by difficulty
- reward by corruption type
- reward by domain

---

## What We Need To Measure

The benchmark should emit:

### Primary metrics

- `similarity`
- `edit_accuracy`
- `collateral_damage`
- `composite_score`
- `exact_match_rate`

### Operational metrics

- latency per example
- tokens per example
- steps per episode
- success rate
- cost per run

### Slices

Break down results by:

- domain
- difficulty
- doc type
- corruption type
- episode length

---

## Benchmark Plan

We should freeze three split families:

1. `train`
2. `validation`
3. `test`

### Proposed first benchmark version

- `train`: broad synthetic coverage for SFT and GRPO
- `validation`: small but representative
- `test`: untouched, fixed, and never used for training

### Reproducibility

Every benchmark case must store:

- `doc_seed`
- `corruption_seed`
- `difficulty`
- `domain`

That is enough to regenerate the exact task.

---

## GPT-5.4 Baseline Plan

Use GPT-5.4 as the strongest baseline.

We should run:

1. direct rewrite baseline
2. optionally tool-call baseline if time allows

For tomorrow’s story, the direct rewrite baseline is enough.

Why:

- simple to implement
- easy to compare against local model
- credible high-end reference

---

## Small Open Model Baseline Plan

Run one open model locally through `vLLM`.

Suggested initial path:

- one `1B-3B` instruct model
- direct rewrite baseline first
- optionally tool policy later

This gives us:

- a pre-finetune floor,
- a local fast-serving baseline,
- a clean comparison against the fine-tuned version.

---

## Fine-Tuning Plan

### Phase 1. SFT warm start

Objective:

- teach markup reconstruction,
- teach structure preservation,
- reduce nonsensical edits.

Inputs:

- source document
- instruction

Targets:

- exact target document

Training approach:

- QLoRA if model is 3B-7B
- full fine-tune only if model is tiny and time permits

Checkpoint goal:

- beats the base model on held-out benchmark

### Phase 2. GRPO

Objective:

- improve exactness on verifier-driven reward,
- reduce collateral damage,
- improve completion rate.

Inputs:

- task manifest
- verifier/game environment

Outputs:

- improved policy checkpoint

Checkpoint goal:

- beats SFT checkpoint on validation benchmark

---

## Fastest Practical Execution Plan Tonight

### Phase A. Product + benchmark stabilization

1. preserve classic UI
2. expose dual seeds in both UIs
3. add launcher options
4. freeze benchmark split generation script
5. scaffold unified eval harness

### Phase B. Baselines

1. run GPT-5.4 direct rewrite benchmark
2. run small open model direct rewrite benchmark via vLLM

### Phase C. Training

1. generate direct rewrite SFT examples from source/target pairs
2. run short SFT warm start
3. evaluate SFT checkpoint
4. run short GRPO overnight
5. evaluate final checkpoint in the morning

---

## Template Recommendation Summary

### Use this

- RunPod `PyTorch` template
- Python `3.11`
- install `vllm` manually

### Do not use as the primary template

- RunPod `vLLM latest` template

Reason:

- that template is inference-first,
- we need training-first plus inference support,
- PyTorch template gives us maximum flexibility.

---

## H200 vs B200

### H200

Best choice tonight.

Why:

- plenty of memory
- very strong performance
- lower cost than B200
- sufficient for small-model SFT + GRPO + vLLM

### B200

Overkill for tonight unless:

- money truly does not matter,
- availability is good,
- you plan multiple concurrent runs.

For your stated goal, the `H200` is the right choice.

---

## Risk Register

### Risk 1. Not enough time to converge

Mitigation:

- keep model small
- do SFT before GRPO
- keep benchmark narrow initially

### Risk 2. Reward hacking

Mitigation:

- inspect collateral damage
- log raw outputs
- compare against exact-match and edit-accuracy, not reward alone

### Risk 3. Format collapse

Mitigation:

- SFT warm start
- strong prompt constraints
- markup-preserving data mix

### Risk 4. vLLM and trainer conflicts

Mitigation:

- use PyTorch template
- run vLLM in a separate process or only during eval/rollout phases

### Risk 5. Benchmark leakage

Mitigation:

- freeze test split early
- never sample held-out split during training

---

## What Success Looks Like By Tomorrow

Minimum successful outcome:

- both UIs demo cleanly
- dual seeds are exposed
- benchmark split is frozen
- eval harness runs
- GPT-5.4 baseline completes
- one open-model baseline completes
- at least one SFT or GRPO checkpoint produces measurable uplift

Strong successful outcome:

- SFT beats base model
- GRPO beats SFT on validation
- we can show a table comparing:
  - GPT-5.4
  - base local model
  - SFT model
  - SFT + GRPO model

---

## Final Go / No-Go

### Go

- `H200`
- `Secure Cloud`
- `PyTorch / Python 3.11 template`
- `600GB` network volume
- install and use `vLLM` inside that environment

That is the right setup for tonight.
