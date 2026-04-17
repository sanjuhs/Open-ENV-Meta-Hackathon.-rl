#!/usr/bin/env python3
"""Build a markdown report for a Love Game training snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


RUNS = [
    ("reward_model_v2", "Reward Model (DistilRoBERTa)", "reward_model"),
    ("smol_135m_sft_v3", "SmolLM2-135M SFT", "sft"),
    ("smol_135m_sft_dpo_v2", "SmolLM2-135M SFT+DPO", "dpo"),
    ("smol_135m_sft_dpo_grpo_v1", "SmolLM2-135M SFT+DPO+GRPO", "grpo"),
    ("reward_model_ppo_v1", "PPO-Compatible Reward Model", "reward_model"),
    ("smol_135m_sft_dpo_ppo_v1", "SmolLM2-135M SFT+DPO+PPO", "ppo"),
]


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_metrics(metrics: dict | None) -> str:
    if not metrics:
        return "-"
    interesting = [
        "eval_loss",
        "eval_accuracy",
        "reward",
        "reward_std",
        "train_loss",
    ]
    parts = []
    for key in interesting:
        if key in metrics:
            parts.append(f"{key}={metrics[key]:.4f}" if isinstance(metrics[key], (int, float)) else f"{key}={metrics[key]}")
    return ", ".join(parts) if parts else "-"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, help="Snapshot name, e.g. 20260418_2m_snapshot")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    love_dir = args.root / "love_game"
    snapshot = args.snapshot
    checkpoints_dir = love_dir / "checkpoints" / snapshot
    logs_dir = love_dir / "logs" / snapshot
    splits_dir = love_dir / "splits" / snapshot
    reports_dir = love_dir / "reports" / snapshot
    reports_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_json(splits_dir / "manifest.json") or {}
    rows = []
    for dirname, label, kind in RUNS:
        out_dir = checkpoints_dir / dirname
        metrics = load_json(out_dir / "final_metrics.json")
        trainer_state = out_dir / "trainer_state.json"
        chart_path = reports_dir / f"{dirname}_plots" / "loss_chart.svg"
        rows.append(
            {
                "label": label,
                "kind": kind,
                "dir": out_dir,
                "metrics": metrics,
                "trainer_state": trainer_state if trainer_state.exists() else None,
                "chart_path": chart_path if chart_path.exists() else None,
            }
        )

    table_lines = [
        "| Run | Type | Status | Key metrics |",
        "|---|---|---|---|",
    ]
    for row in rows:
        status = "done" if row["metrics"] else "pending"
        table_lines.append(
            f"| {row['label']} | {row['kind']} | {status} | {summarize_metrics(row['metrics'])} |"
        )

    manifest_block = json.dumps(manifest, indent=2) if manifest else "{}"
    report = f"""# Love Game Snapshot Report

Snapshot: `{snapshot}`

## Split Summary

```json
{manifest_block}
```

## Run Table

{chr(10).join(table_lines)}

## Notes

- `reward_model_v2` is the DistilRoBERTa-style analyzer reward model.
- `reward_model_ppo_v1` is the PPO-compatible reward model with a causal-LM scoring head.
- `smol_135m_sft_dpo_grpo_v1` is driven by a mixed reward:
  - learned reward model
  - rule-based Love Game reward
- `smol_135m_sft_dpo_ppo_v1` depends on the PPO-compatible reward model.

## Logs

- Logs live under: `{logs_dir}`
- Checkpoints live under: `{checkpoints_dir}`
"""

    out_path = reports_dir / "REPORT.md"
    out_path.write_text(report, encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
