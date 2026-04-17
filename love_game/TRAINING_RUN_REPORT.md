# Love Game Tiny-Model Training Report

Date: 2026-04-18  
Hardware: `1x H200 SXM` on RunPod

## Goal

Train a very small model on the fictional `Aditi` character data and get real training artifacts:

- train/validation splits
- validation loss
- loss curves
- before/after generations

## Model

- Base model: `HuggingFaceTB/SmolLM2-135M-Instruct`

## Data

Split manifest from [love_game/splits/manifest.json](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/splits/manifest.json):

- `SFT`: `144` train / `18` validation / `18` test
- `RLHF pairs`: `109` train / `13` validation / `13` test
- `Reward model pointwise`: `216` train / `27` validation / `27` test

## What We Ran

### 1. Full SFT

Script:
- [run_sft_full.py](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/run_sft_full.py)

Artifacts:
- metrics: [sft_final_metrics.json](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/remote_metrics/sft_final_metrics.json)
- samples: [sft_samples.json](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/runs/sft_samples.json)
- plots: [loss_points.json](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/runs/sft_v1_plots/loss_points.json), [loss_chart.svg](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/runs/sft_v1_plots/loss_chart.svg)

Final validation loss:
- `3.6167`

Observation:
- validation loss steadily improved from about `3.79` to about `3.62`
- the model learned some of the dataset distribution
- generations were still repetitive and weak

### 2. Full DPO on top of the SFT checkpoint

Script:
- [run_dpo_full.py](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/run_dpo_full.py)

Artifacts:
- metrics: [dpo_final_metrics.json](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/remote_metrics/dpo_final_metrics.json)
- samples: [dpo_samples.json](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/runs/dpo_samples.json)
- plots: [loss_points.json](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/runs/dpo_v1_plots/loss_points.json), [loss_chart.svg](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/runs/dpo_v1_plots/loss_chart.svg)

Final validation loss:
- `0.4888` on the DPO objective

Observation:
- preference margins improved strongly
- reward accuracy on the tiny validation split stayed very high
- generation quality still remained weak in absolute terms

## Before / After

Base sample:
- [base_samples.json](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/runs/base_samples.json)

Summary:
- base model was bland, repetitive, and frequently slipped into generic filler

SFT sample:
- [sft_samples.json](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/runs/sft_samples.json)

Summary:
- SFT made the model slightly more anchored to the prompt
- but it still looped badly and did not sound convincingly like the target character

DPO sample:
- [dpo_samples.json](/Users/sanju/Desktop/coding/python/open-env-meta/love_game/runs/dpo_samples.json)

Summary:
- DPO sharpened the preference objective
- but the `135M` model still lacked enough capacity to produce high-quality outputs reliably

## Honest Conclusion

This was a successful **training pipeline** run, but not yet a successful **character model**.

What worked:

- dataset pipeline
- split generation
- H200 training
- validation logging
- SVG loss-curve export
- sample generation and checkpoint comparison

What did not fully work:

- the `135M` model is still too small to carry this personality well
- outputs remain repetitive and underpowered even after SFT + DPO

## Best Talk Framing

This is actually a strong teaching result:

> "We can absolutely train the tiny model. The loss improves. The preference objective improves. But the model still feels dumb. That is the point: better optimization does not magically create enough capacity."

## What I Would Try Next

1. Use a slightly larger base model such as `0.5B` or `1.5B`.
2. Increase data variety further, especially shorter high-signal conversations.
3. Train with shorter max lengths and more aggressive curriculum.
4. Add a small repetition penalty at generation time for demos.
5. Keep the `135M` run as the funny baseline that visibly struggles.
