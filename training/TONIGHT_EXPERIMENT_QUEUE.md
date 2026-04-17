# Tonight Experiment Queue

Date:
- April 17, 2026

Hardware:
- `1x H200 SXM`

Main model:
- `Qwen/Qwen2.5-3B-Instruct`

Training style:
- `LoRA SFT` first
- then `LoRA GRPO` on top of the SFT adapter

## What GRPO Is Updating

We are **not** full-fine-tuning the entire 3B model.

We are doing:
1. `SFT` to create a LoRA adapter
2. `GRPO` continuing from that adapter

So yes:
- GRPO is operating on the LoRA-adapted model
- the base model stays mostly frozen
- the trainable part is the adapter

That is why this is fast enough to do on one H200.

## Queue

| Order | Experiment | Model / Weights | Method | Approx time | Expected output |
|---|---:|---|---|---:|---|
| 1 | Running now | `Qwen2.5-3B + SFT LoRA` | `GRPO`, `100` steps total | about `95-110 min` total from start, about `80-90 min` remained when queued | `qwen25_3b_grpo` adapter directory plus learning logs |
| 2 | Queued after GRPO | `Qwen2.5-3B + GRPO LoRA` | local eval on `10` validation cases | about `8-12 min` | `training/runs/qwen25_3b_grpo_10.jsonl` with post-RL scores |
| 3 | Queued after GRPO eval | `Qwen2.5-3B + SFT LoRA` | local eval on `10` validation cases | about `8-12 min` | `training/runs/qwen25_3b_sft_10.jsonl` |
| 4 | Queued after SFT eval | base `Qwen2.5-3B-Instruct` | local eval on `10` validation cases | about `6-10 min` | `training/runs/qwen25_3b_base_10.jsonl` |

## Already Completed

| Experiment | Model / Weights | Method | Time | Output |
|---|---|---|---:|---|
| Dataset build | synthetic DocEdit cases | dataset generation | under `1 min` | `sft_train.jsonl`, `grpo_train.jsonl`, validation files |
| Base smoke eval | base `Qwen2.5-3B-Instruct` | local eval, `2` validation cases | about `1-2 min` load + `~34s/case` | `qwen25_3b_base_smoke.jsonl` |
| SFT training | `Qwen2.5-3B-Instruct` -> SFT LoRA | supervised fine-tuning | about `109s` | `training/checkpoints/qwen25_3b_sft` |
| SFT smoke eval | `Qwen2.5-3B + SFT LoRA` | local eval, `2` validation cases | about `1-2 min` load + `~45s/case` | `qwen25_3b_sft_smoke.jsonl` |

## Latest Live GRPO Snapshot

At the last check:
- progress: about `17 / 100` steps
- GPU memory: about `33.5 GB`
- GPU utilization: about `30%` at the exact sample, higher during generation bursts
- recent rewards:
  - step `5`: about `0.8422`
  - step `10`: about `0.7638`
  - step `15`: about `0.9102`

## What We Get At The End

After this queue finishes, we will have:

1. a base-model score on `10` held-out validation cases
2. an SFT-LoRA score on the same `10` cases
3. a GRPO-on-LoRA score on the same `10` cases
4. a clean three-way comparison:
   - base
   - SFT
   - SFT + GRPO

That is the core experiment story for tomorrow.
