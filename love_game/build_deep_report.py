#!/usr/bin/env python3
"""Build a presentation-ready Love Game report with SVG plots."""

from __future__ import annotations

import argparse
import json
import math
import textwrap
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
LOVE_DIR = ROOT / "love_game"

RUN_LABELS = {
    "reward_model_v2": "Reward Model v2 (DistilRoBERTa)",
    "smol_135m_sft_v3": "SmolLM2-135M-Instruct + SFT",
    "smol_135m_sft_dpo_v2": "SmolLM2-135M-Instruct + SFT + DPO",
    "smol_135m_sft_dpo_grpo_v1": "SmolLM2-135M-Instruct + SFT + DPO + GRPO",
    "reward_model_ppo_v1": "PPO-Compatible Reward Model",
    "smol_135m_sft_dpo_ppo_v1": "SmolLM2-135M-Instruct + SFT + DPO + PPO",
}

HF_MODEL_REPO = "https://huggingface.co/sanjuhs/love-game-smollm2-135m-suite"
HF_DATASET_REPO = "https://huggingface.co/datasets/sanjuhs/adt-personality-dataset"
BASE_MODEL_LINK = "https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct"
REWARD_MODEL_BASE_LINK = "https://huggingface.co/distilroberta-base"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def wrap(text: str, width: int = 88) -> str:
    return "\n".join(textwrap.wrap(text, width=width)) if text else ""


def latest_trainer_state(states_root: Path, run_name: str) -> tuple[Path | None, dict | None]:
    run_root = states_root / run_name
    if not run_root.exists():
        return None, None
    candidates = sorted(
        run_root.glob("checkpoint-*/trainer_state.json"),
        key=lambda path: int(path.parent.name.split("-")[-1]),
    )
    if not candidates:
        return None, None
    path = candidates[-1]
    return path, load_json(path)


def write_svg(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def line_chart_svg(
    series: list[tuple[str, list[tuple[float, float]], str]],
    *,
    title: str,
    width: int = 960,
    height: int = 460,
    y_label: str = "",
    x_label: str = "step",
) -> str:
    all_points = [point for _, points, _ in series for point in points]
    if not all_points:
        return f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}'></svg>"

    min_x = min(point[0] for point in all_points)
    max_x = max(point[0] for point in all_points)
    min_y = min(point[1] for point in all_points)
    max_y = max(point[1] for point in all_points)
    if min_x == max_x:
        max_x += 1
    if min_y == max_y:
        max_y += 1

    pad_left = 70
    pad_right = 30
    pad_top = 45
    pad_bottom = 55

    def sx(value: float) -> float:
        return pad_left + (value - min_x) / (max_x - min_x) * (width - pad_left - pad_right)

    def sy(value: float) -> float:
        return height - pad_bottom - (value - min_y) / (max_y - min_y) * (height - pad_top - pad_bottom)

    def path_for(points: list[tuple[float, float]]) -> str:
        return " ".join(
            f"{'M' if index == 0 else 'L'} {sx(x):.2f},{sy(y):.2f}"
            for index, (x, y) in enumerate(points)
        )

    grid = []
    for idx in range(5):
        y = pad_top + idx * (height - pad_top - pad_bottom) / 4
        grid.append(f"<line x1='{pad_left}' y1='{y:.2f}' x2='{width-pad_right}' y2='{y:.2f}' stroke='#e6ddcf' />")
        tick_value = max_y - idx * (max_y - min_y) / 4
        grid.append(
            f"<text x='{pad_left-10}' y='{y+4:.2f}' text-anchor='end' font-size='12' fill='#725f4a'>{tick_value:.3g}</text>"
        )

    x_ticks = []
    for idx in range(5):
        x = pad_left + idx * (width - pad_left - pad_right) / 4
        tick_value = min_x + idx * (max_x - min_x) / 4
        x_ticks.append(f"<line x1='{x:.2f}' y1='{height-pad_bottom}' x2='{x:.2f}' y2='{pad_top}' stroke='#f4ede2' />")
        x_ticks.append(
            f"<text x='{x:.2f}' y='{height-pad_bottom+20}' text-anchor='middle' font-size='12' fill='#725f4a'>{tick_value:.0f}</text>"
        )

    legend = []
    legend_x = pad_left
    legend_y = 24
    for index, (name, _, color) in enumerate(series):
        x = legend_x + index * 210
        legend.append(f"<line x1='{x}' y1='{legend_y}' x2='{x+20}' y2='{legend_y}' stroke='{color}' stroke-width='4' />")
        legend.append(f"<text x='{x+28}' y='{legend_y+4}' font-size='13' fill='#2e261d'>{html_escape(name)}</text>")

    paths = [
        f"<path d='{path_for(points)}' fill='none' stroke='{color}' stroke-width='3.2' stroke-linejoin='round' stroke-linecap='round' />"
        for _, points, color in series
        if points
    ]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
  <rect width="100%" height="100%" fill="#fcf8f2"/>
  <rect x="0" y="0" width="100%" height="44" fill="#f2e8d9"/>
  <text x="{pad_left}" y="28" font-size="22" font-weight="700" fill="#2e261d">{html_escape(title)}</text>
  {''.join(grid)}
  {''.join(x_ticks)}
  <line x1="{pad_left}" y1="{height-pad_bottom}" x2="{width-pad_right}" y2="{height-pad_bottom}" stroke="#8d7760" stroke-width="1.5" />
  <line x1="{pad_left}" y1="{pad_top}" x2="{pad_left}" y2="{height-pad_bottom}" stroke="#8d7760" stroke-width="1.5" />
  {''.join(paths)}
  {''.join(legend)}
  <text x="{width/2:.2f}" y="{height-12}" text-anchor="middle" font-size="13" fill="#725f4a">{html_escape(x_label)}</text>
  <text x="18" y="{height/2:.2f}" transform="rotate(-90 18 {height/2:.2f})" text-anchor="middle" font-size="13" fill="#725f4a">{html_escape(y_label)}</text>
</svg>"""


def bar_chart_svg(
    items: list[tuple[str, float, str]],
    *,
    title: str,
    width: int = 980,
    height: int = 460,
    y_label: str = "",
) -> str:
    if not items:
        return f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}'></svg>"

    pad_left = 70
    pad_right = 30
    pad_top = 60
    pad_bottom = 130
    max_val = max(value for _, value, _ in items) or 1
    usable_width = width - pad_left - pad_right
    bar_width = usable_width / max(1, len(items)) * 0.66
    gap = usable_width / max(1, len(items))

    bars = []
    labels = []
    for idx, (label, value, color) in enumerate(items):
        x = pad_left + idx * gap + (gap - bar_width) / 2
        bar_height = (value / max_val) * (height - pad_top - pad_bottom)
        y = height - pad_bottom - bar_height
        bars.append(f"<rect x='{x:.2f}' y='{y:.2f}' width='{bar_width:.2f}' height='{bar_height:.2f}' fill='{color}' rx='6' />")
        bars.append(
            f"<text x='{x + bar_width / 2:.2f}' y='{y - 8:.2f}' text-anchor='middle' font-size='12' fill='#4a3a2a'>{value:,.0f}</text>"
        )
        labels.append(
            f"<text x='{x + bar_width / 2:.2f}' y='{height-pad_bottom+18:.2f}' text-anchor='middle' font-size='12' fill='#4a3a2a'>{html_escape(label)}</text>"
        )

    grid = []
    for idx in range(5):
        y = pad_top + idx * (height - pad_top - pad_bottom) / 4
        tick = max_val - idx * max_val / 4
        grid.append(f"<line x1='{pad_left}' y1='{y:.2f}' x2='{width-pad_right}' y2='{y:.2f}' stroke='#ece2d4' />")
        grid.append(
            f"<text x='{pad_left-8}' y='{y+4:.2f}' text-anchor='end' font-size='12' fill='#725f4a'>{tick:,.0f}</text>"
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
  <rect width="100%" height="100%" fill="#fcf8f2"/>
  <rect x="0" y="0" width="100%" height="46" fill="#f2e8d9"/>
  <text x="{pad_left}" y="30" font-size="22" font-weight="700" fill="#2e261d">{html_escape(title)}</text>
  {''.join(grid)}
  <line x1="{pad_left}" y1="{height-pad_bottom}" x2="{width-pad_right}" y2="{height-pad_bottom}" stroke="#8d7760" stroke-width="1.5" />
  <line x1="{pad_left}" y1="{pad_top}" x2="{pad_left}" y2="{height-pad_bottom}" stroke="#8d7760" stroke-width="1.5" />
  {''.join(bars)}
  {''.join(labels)}
  <text x="18" y="{height/2:.2f}" transform="rotate(-90 18 {height/2:.2f})" text-anchor="middle" font-size="13" fill="#725f4a">{html_escape(y_label)}</text>
</svg>"""


def latest_checkpoint_number(run_dir: Path) -> int | None:
    candidates = []
    for child in run_dir.iterdir():
        if child.is_dir() and child.name.startswith("checkpoint-"):
            try:
                candidates.append(int(child.name.split("-")[-1]))
            except ValueError:
                pass
    return max(candidates) if candidates else None


def summarize_samples(sample_path: Path) -> dict | None:
    if not sample_path.exists():
        return None
    data = load_json(sample_path)
    if not data:
        return None
    first = data[0]
    return {
        "scenario_id": first.get("scenario_id", ""),
        "reference": first.get("reference", ""),
        "generated": first.get("generated", ""),
    }


def short_json_block(row: dict, keys: Iterable[str], limit: int = 1400) -> str:
    block = {key: row.get(key) for key in keys if key in row}
    text = json.dumps(block, indent=2, ensure_ascii=False)
    return text[:limit] + ("\n..." if len(text) > limit else "")


def code_snippet(path: Path, start: int, end: int) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    selected = []
    for line_no in range(start, end + 1):
        selected.append(lines[line_no - 1])
    return "\n".join(selected)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", default="20260418_2m_snapshot")
    args = parser.parse_args()

    report_dir = LOVE_DIR / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = report_dir / "assets" / args.snapshot
    assets_dir.mkdir(parents=True, exist_ok=True)
    states_root = assets_dir / "trainer_states"
    splits_root = assets_dir / "splits"

    manifest = load_json(splits_root / "manifest.json")
    token_counts = load_json(assets_dir / "snapshot_token_counts.json")

    checkpoints_root = LOVE_DIR / "local_backups" / args.snapshot
    sample_root = LOVE_DIR / "remote_samples" / args.snapshot

    final_metrics = {
        "reward_model_v2": load_json(checkpoints_root / "reward_model_v2" / "final_metrics.json"),
        "smol_135m_sft_v3": load_json(checkpoints_root / "smol_135m_sft_v3" / "final_metrics.json"),
        "smol_135m_sft_dpo_v2": load_json(checkpoints_root / "smol_135m_sft_dpo_v2" / "final_metrics.json"),
        "smol_135m_sft_dpo_grpo_v1": load_json(checkpoints_root / "smol_135m_sft_dpo_grpo_v1" / "final_metrics.json"),
        "reward_model_ppo_v1": load_json(checkpoints_root / "reward_model_ppo_v1" / "final_metrics.json"),
    }

    ppo_state_path, ppo_state = latest_trainer_state(states_root, "smol_135m_sft_dpo_ppo_v1")
    grpo_state_path, grpo_state = latest_trainer_state(states_root, "smol_135m_sft_dpo_grpo_v1")
    sft_state_path, sft_state = latest_trainer_state(states_root, "smol_135m_sft_v3")
    dpo_state_path, dpo_state = latest_trainer_state(states_root, "smol_135m_sft_dpo_v2")
    rm_state_path, rm_state = latest_trainer_state(states_root, "reward_model_v2")
    rm_ppo_state_path, rm_ppo_state = latest_trainer_state(states_root, "reward_model_ppo_v1")

    # Charts
    write_svg(
        assets_dir / "sft_loss_curve.svg",
        line_chart_svg(
            [
                ("train loss", [(item["step"], item["loss"]) for item in sft_state["log_history"] if "loss" in item and "step" in item], "#c35b31"),
                ("eval loss", [(item["step"], item["eval_loss"]) for item in sft_state["log_history"] if "eval_loss" in item and "step" in item], "#2d6a4f"),
            ],
            title="SFT Loss Curve",
            y_label="loss",
        ),
    )
    write_svg(
        assets_dir / "reward_model_v2_curve.svg",
        line_chart_svg(
            [
                ("train loss", [(item["step"], item["loss"]) for item in rm_state["log_history"] if "loss" in item and "step" in item], "#b95b39"),
                ("eval loss", [(item["step"], item["eval_loss"]) for item in rm_state["log_history"] if "eval_loss" in item and "step" in item], "#3c7c59"),
                ("eval accuracy", [(item["step"], item["eval_accuracy"]) for item in rm_state["log_history"] if "eval_accuracy" in item and "step" in item], "#3366aa"),
            ],
            title="Reward Model v2 Training",
            y_label="loss / accuracy",
        ),
    )
    write_svg(
        assets_dir / "dpo_curve.svg",
        line_chart_svg(
            [
                ("train loss", [(item["step"], item["loss"]) for item in dpo_state["log_history"] if "loss" in item and "step" in item], "#bd5e38"),
                ("eval loss", [(item["step"], item["eval_loss"]) for item in dpo_state["log_history"] if "eval_loss" in item and "step" in item], "#2f7a57"),
                ("eval pref acc", [(item["step"], item["eval_rewards/accuracies"]) for item in dpo_state["log_history"] if "eval_rewards/accuracies" in item and "step" in item], "#3b63a7"),
            ],
            title="DPO Training",
            y_label="loss / preference accuracy",
        ),
    )
    write_svg(
        assets_dir / "grpo_rewards.svg",
        line_chart_svg(
            [
                ("total reward", [(item["step"], item["reward"]) for item in grpo_state["log_history"] if "reward" in item and "step" in item], "#c15834"),
                ("learned reward", [(item["step"], item["rewards/learned_reward_model/mean"]) for item in grpo_state["log_history"] if "rewards/learned_reward_model/mean" in item and "step" in item], "#26547c"),
                ("rule reward", [(item["step"], item["rewards/rule_reward/mean"]) for item in grpo_state["log_history"] if "rewards/rule_reward/mean" in item and "step" in item], "#2d7d46"),
            ],
            title="GRPO Reward Composition",
            y_label="reward",
        ),
    )
    write_svg(
        assets_dir / "grpo_step_time.svg",
        line_chart_svg(
            [
                ("step time", [(item["step"], item["step_time"]) for item in grpo_state["log_history"] if "step_time" in item and "step" in item], "#7a4cc2"),
            ],
            title="GRPO Step Time",
            y_label="seconds",
        ),
    )
    write_svg(
        assets_dir / "ppo_reward_curve.svg",
        line_chart_svg(
            [
                ("rlhf reward", [(item["step"], item["objective/rlhf_reward"]) for item in ppo_state["log_history"] if "objective/rlhf_reward" in item and "step" in item], "#ba5830"),
                ("score", [(item["step"], item["objective/scores"]) for item in ppo_state["log_history"] if "objective/scores" in item and "step" in item], "#2f7a57"),
                ("KL", [(item["step"], item["objective/kl"]) for item in ppo_state["log_history"] if "objective/kl" in item and "step" in item], "#355fa3"),
            ],
            title="PPO Online RL Signals",
            y_label="score / reward / kl",
        ),
    )
    write_svg(
        assets_dir / "reward_model_ppo_curve.svg",
        line_chart_svg(
            [
                ("train loss", [(item["step"], item["loss"]) for item in rm_ppo_state["log_history"] if "loss" in item and "step" in item], "#bb5a36"),
                ("accuracy", [(item["step"], item["accuracy"]) for item in rm_ppo_state["log_history"] if "accuracy" in item and "step" in item], "#315da8"),
                ("margin", [(item["step"], item["margin"]) for item in rm_ppo_state["log_history"] if "margin" in item and "step" in item], "#2d7b59"),
            ],
            title="PPO-Compatible Reward Model",
            y_label="loss / accuracy / margin",
        ),
    )

    token_items = [
        ("SFT text", token_counts["sft"]["train"]["text_tokens"] + token_counts["sft"]["validation"]["text_tokens"] + token_counts["sft"]["test"]["text_tokens"], "#c25a31"),
        ("DPO", token_counts["dpo"]["train"]["json_tokens"] + token_counts["dpo"]["validation"]["json_tokens"] + token_counts["dpo"]["test"]["json_tokens"], "#355fa3"),
        ("RM pointwise", token_counts["rm_pointwise"]["train"]["json_tokens"] + token_counts["rm_pointwise"]["validation"]["json_tokens"] + token_counts["rm_pointwise"]["test"]["json_tokens"], "#2f7a57"),
        ("PPO prompts", token_counts["ppo"]["train"]["json_tokens"] + token_counts["ppo"]["validation"]["json_tokens"] + token_counts["ppo"]["test"]["json_tokens"], "#8661c5"),
        ("GRPO prompts", token_counts["grpo"]["train"]["json_tokens"] + token_counts["grpo"]["validation"]["json_tokens"] + token_counts["grpo"]["test"]["json_tokens"], "#c08a2a"),
    ]
    write_svg(
        assets_dir / "dataset_token_budget.svg",
        bar_chart_svg(token_items, title="Snapshot Token Budget by Training Objective", y_label="approximate tokens"),
    )

    summary_rows = [
        {
            "run": "reward_model_v2",
            "label": RUN_LABELS["reward_model_v2"],
            "final_eval_loss": final_metrics["reward_model_v2"]["eval_loss"],
            "extra": {"eval_accuracy": final_metrics["reward_model_v2"]["eval_accuracy"]},
            "checkpoint": latest_checkpoint_number(checkpoints_root / "reward_model_v2"),
        },
        {
            "run": "smol_135m_sft_v3",
            "label": RUN_LABELS["smol_135m_sft_v3"],
            "final_eval_loss": final_metrics["smol_135m_sft_v3"]["eval_loss"],
            "extra": {"epoch": final_metrics["smol_135m_sft_v3"]["epoch"]},
            "checkpoint": latest_checkpoint_number(checkpoints_root / "smol_135m_sft_v3"),
        },
        {
            "run": "smol_135m_sft_dpo_v2",
            "label": RUN_LABELS["smol_135m_sft_dpo_v2"],
            "final_eval_loss": final_metrics["smol_135m_sft_dpo_v2"]["eval_loss"],
            "extra": {},
            "checkpoint": latest_checkpoint_number(checkpoints_root / "smol_135m_sft_dpo_v2"),
        },
        {
            "run": "smol_135m_sft_dpo_grpo_v1",
            "label": RUN_LABELS["smol_135m_sft_dpo_grpo_v1"],
            "final_eval_loss": final_metrics["smol_135m_sft_dpo_grpo_v1"]["eval_loss"],
            "extra": {},
            "checkpoint": latest_checkpoint_number(checkpoints_root / "smol_135m_sft_dpo_grpo_v1"),
        },
        {
            "run": "reward_model_ppo_v1",
            "label": RUN_LABELS["reward_model_ppo_v1"],
            "final_eval_loss": final_metrics["reward_model_ppo_v1"]["eval_loss"],
            "extra": {},
            "checkpoint": latest_checkpoint_number(checkpoints_root / "reward_model_ppo_v1"),
        },
        {
            "run": "smol_135m_sft_dpo_ppo_v1",
            "label": RUN_LABELS["smol_135m_sft_dpo_ppo_v1"],
            "final_eval_loss": None,
            "extra": {
                "episodes": ppo_state["episode"],
                "global_step": ppo_state["global_step"],
                "last_rlhf_reward": ppo_state["log_history"][-1]["objective/rlhf_reward"],
                "last_score": ppo_state["log_history"][-1]["objective/scores"],
            },
            "checkpoint": latest_checkpoint_number(checkpoints_root / "smol_135m_sft_dpo_ppo_v1"),
        },
    ]
    (assets_dir / "summary_table.json").write_text(json.dumps(summary_rows, indent=2), encoding="utf-8")

    sample_sets = {
        "base": summarize_samples(sample_root / "base_samples.json"),
        "sft": summarize_samples(sample_root / "sft_samples.json"),
        "dpo": summarize_samples(sample_root / "dpo_samples.json"),
        "grpo": summarize_samples(sample_root / "grpo_samples.json"),
        "ppo": summarize_samples(sample_root / "ppo_samples.json"),
    }
    (assets_dir / "sample_summary.json").write_text(json.dumps(sample_sets, indent=2, ensure_ascii=False), encoding="utf-8")

    sft_example = read_jsonl(splits_root / "sft_train.jsonl")[0]
    dpo_example = read_jsonl(splits_root / "dpo_train.jsonl")[0]
    rm_example = read_jsonl(splits_root / "rm_pointwise_train.jsonl")[0]
    ppo_example = read_jsonl(splits_root / "ppo_train.jsonl")[0]
    grpo_example = read_jsonl(splits_root / "grpo_train.jsonl")[0]

    total_sft_text_tokens = sum(token_counts["sft"][split]["text_tokens"] for split in ("train", "validation", "test"))
    total_dpo_tokens = sum(token_counts["dpo"][split]["json_tokens"] for split in ("train", "validation", "test"))
    total_rm_tokens = sum(token_counts["rm_pointwise"][split]["json_tokens"] for split in ("train", "validation", "test"))
    total_ppo_tokens = sum(token_counts["ppo"][split]["json_tokens"] for split in ("train", "validation", "test"))
    total_grpo_tokens = sum(token_counts["grpo"][split]["json_tokens"] for split in ("train", "validation", "test"))

    summary_table_lines = [
        "| Stage | Base / Initialization | Train split | Validation split | Final metric | Notes |",
        "|---|---|---:|---:|---|---|",
        f"| Reward model v2 | [`distilroberta-base`]({REWARD_MODEL_BASE_LINK}) | {manifest['rm_pointwise']['train']} | {manifest['rm_pointwise']['validation']} | eval_accuracy=`{final_metrics['reward_model_v2']['eval_accuracy']:.4f}` | Pointwise reward classifier; useful but noisy |",
        f"| SFT | [`SmolLM2-135M-Instruct`]({BASE_MODEL_LINK}) | {manifest['sft']['train']} | {manifest['sft']['validation']} | eval_loss=`{final_metrics['smol_135m_sft_v3']['eval_loss']:.4f}` | Full-weight supervised tuning |",
        f"| DPO | SFT-initialized policy | {manifest['dpo']['train']} | {manifest['dpo']['validation']} | eval_loss=`{final_metrics['smol_135m_sft_dpo_v2']['eval_loss']:.4f}` | Preference optimization on chosen vs rejected pairs |",
        f"| GRPO | SFT+DPO policy | {manifest['grpo']['train']} | {manifest['grpo']['validation']} | eval_loss=`{final_metrics['smol_135m_sft_dpo_grpo_v1']['eval_loss']:.4e}` | Mixed rule reward + learned reward scorer |",
        f"| PPO reward model | [`SmolLM2-135M-Instruct`]({BASE_MODEL_LINK}) reward head | {manifest['dpo']['train']} | {manifest['dpo']['validation']} | eval_loss=`{final_metrics['reward_model_ppo_v1']['eval_loss']:.4e}` | Causal-LM-compatible reward scorer for PPO |",
        f"| PPO | SFT+DPO policy + PPO reward model | prompt-only `ppo_train={manifest['ppo']['train']}` | `ppo_validation={manifest['ppo']['validation']}` | last score=`{ppo_state['log_history'][-1]['objective/scores']:.4f}` | Short 64-episode run; no separate final eval file |",
    ]

    sample_comparison_lines = [
        "| Model | Sample output excerpt |",
        "|---|---|",
    ]
    for key in ["base", "sft", "dpo", "grpo", "ppo"]:
        sample = sample_sets[key]
        if sample is None:
            continue
        excerpt = sample["generated"].replace("\n", " ").strip()
        excerpt = excerpt[:220] + ("..." if len(excerpt) > 220 else "")
        sample_comparison_lines.append(f"| {key.upper()} | {excerpt} |")

    dataset_table_lines = [
        "| Dataset family | Train rows | Validation rows | Test rows | Approx tokens |",
        "|---|---:|---:|---:|---:|",
        f"| SFT formatted text | {manifest['sft']['train']} | {manifest['sft']['validation']} | {manifest['sft']['test']} | {total_sft_text_tokens:,} |",
        f"| DPO / RLHF pairs | {manifest['dpo']['train']} | {manifest['dpo']['validation']} | {manifest['dpo']['test']} | {total_dpo_tokens:,} |",
        f"| Reward-model pointwise | {manifest['rm_pointwise']['train']} | {manifest['rm_pointwise']['validation']} | {manifest['rm_pointwise']['test']} | {total_rm_tokens:,} |",
        f"| PPO prompt-only | {manifest['ppo']['train']} | {manifest['ppo']['validation']} | {manifest['ppo']['test']} | {total_ppo_tokens:,} |",
        f"| GRPO prompt+reward | {manifest['grpo']['train']} | {manifest['grpo']['validation']} | {manifest['grpo']['test']} | {total_grpo_tokens:,} |",
    ]

    model_subpaths = {
        "smol_135m_sft_v3": f"{HF_MODEL_REPO}/tree/main/smol_135m_sft_v3",
        "smol_135m_sft_dpo_v2": f"{HF_MODEL_REPO}/tree/main/smol_135m_sft_dpo_v2",
        "smol_135m_sft_dpo_grpo_v1": f"{HF_MODEL_REPO}/tree/main/smol_135m_sft_dpo_grpo_v1",
        "reward_model_v2": f"{HF_MODEL_REPO}/tree/main/reward_model_v2",
        "reward_model_ppo_v1": f"{HF_MODEL_REPO}/tree/main/reward_model_ppo_v1",
        "smol_135m_sft_dpo_ppo_v1": f"{HF_MODEL_REPO}/tree/main/smol_135m_sft_dpo_ppo_v1",
        "docs": f"{HF_MODEL_REPO}/tree/main/docs",
        "samples": f"{HF_MODEL_REPO}/tree/main/samples",
        "metrics": f"{HF_MODEL_REPO}/tree/main/metrics",
    }

    report = f"""# Love Game: Full Training Report

Author: `sanjuhs123@gmail.com`  
Date: `2026-04-18`  
Snapshot: `{args.snapshot}`

## 1. Executive Summary

Love Game was a fast, end-to-end experiment in teaching a **very small conversational model** to act like a fictional Bangalore-based character named **Aditi** using multiple modern post-training techniques:

- full-weight **SFT**
- **DPO** over chosen/rejected preference pairs
- a classical neural **reward model**
- **GRPO** with a mixed learned + rule reward
- **PPO** with a PPO-compatible reward model

The project was intentionally built as a teaching artifact. The point was not just to get a tiny `135M` model to sound better; it was to make the entire RLHF-style stack visible to students:

- what the datasets look like
- how the training scripts differ
- what reward modeling actually means
- why PPO and GRPO need different ingredients
- where the system improved
- where the tiny model was still obviously limited

The final policy lineage was:

```mermaid
flowchart LR
    A["Base Policy<br/>SmolLM2-135M-Instruct"] --> B["SFT"]
    B --> C["DPO"]
    C --> D["GRPO"]
    C --> E["PPO"]
    A --> F["PPO Reward Model"]
    G["DistilRoBERTa Reward Model"] --> D
```

## 2. Hardware, Platform, and Tooling

### 2.1 Compute

| Item | Value |
|---|---|
| Cloud provider | RunPod |
| Pod type | 1x H200 SXM |
| Available VRAM | ~141 GB |
| Image used | RunPod PyTorch 2.8.0 |
| Inference engine for Love Game training | Standard Transformers / TRL |
| vLLM used for Love Game training | No |
| LoRA used for Love Game | No; this project used **full-weight** updates because `135M` is small enough |

### 2.2 Main external inputs

| Resource | Link | Why it mattered |
|---|---|---|
| Base policy model | [{BASE_MODEL_LINK}]({BASE_MODEL_LINK}) | Starting point for SFT, DPO, PPO, and GRPO |
| Classical reward-model base | [{REWARD_MODEL_BASE_LINK}]({REWARD_MODEL_BASE_LINK}) | First neural reward classifier |
| Dataset backup | [{HF_DATASET_REPO}]({HF_DATASET_REPO}) | Frozen synthetic corpus snapshot |
| Final model bundle | [{HF_MODEL_REPO}]({HF_MODEL_REPO}) | Uploaded Love Game checkpoints and report |

### 2.3 What was actually used

- **Synthetic data generation**: OpenAI API via `love_game/generate_datasets.py` and `love_game/scale_corpus.py`
- **Dataset derivation and split freezing**: `love_game/prepare_training_sets.py` and `love_game/build_training_splits.py`
- **SFT training**: `love_game/run_sft_full.py`
- **DPO training**: `love_game/run_dpo_full.py`
- **Reward-model training (DistilRoBERTa)**: `love_game/run_reward_model_transformer.py`
- **PPO-compatible reward model**: `love_game/run_reward_model_ppo.py`
- **GRPO training**: `love_game/run_grpo.py`
- **PPO training**: `love_game/run_ppo.py`
- **Sampling / inference**: `love_game/sample_generations.py`, `love_game/run_local_inference_suite.py`

## 3. Project Goal

The point of Love Game was to ask a weird but educational question:

> Can a tiny language model be taught a recognizable fictional personality using progressively stronger post-training methods?

The answer, after this run, is:

- **yes**, up to a point
- **SFT** helps a lot
- **DPO** helps refine the behavior
- **reward models** are real but fragile when the data is small/noisy
- **GRPO/PPO** can run, but the quality of the reward signal matters more than the cleverness of the RL acronym

## 4. Character and Data Design

The fictional character was **Aditi**, a playful 26-year-old Bangalore-based graphic designer with:

- Whitefield/Jayanagar commute references
- gym / walking / dosa / ice-cream / reels / football flavor
- playful, affectionate, chaotic tone
- mostly English with light Hinglish / Kannada mixing
- fast bursty texting patterns
- “golden retriever energy” and fast anger release

The character profile lives in:

- [`love_game/RAW_BIO.md`](../RAW_BIO.md)
- [`love_game/CHARACTER_PROFILE.md`](../CHARACTER_PROFILE.md)
- [`love_game/character_profile.json`](../character_profile.json)

The idea was not “general intelligence.”  
It was **stylized consistency under multiple training regimes**.

## 5. Dataset Families

The project intentionally included **different dataset shapes for different training regimes**.

### 5.1 Why the datasets look different

| Technique | Needed data shape | Why |
|---|---|---|
| SFT | `prompt -> ideal reply` | Learn direct next-token behavior |
| DPO | `prompt + chosen + rejected` | Learn preference between two candidate replies |
| Reward modeling | `prompt + reply -> score` or pairwise preference | Learn a scalar notion of better/worse |
| PPO | prompt-only rollouts + reward model | Generate replies online and optimize against reward |
| GRPO | prompt-only rollouts + grouped reward functions | Compare multiple sampled completions under a reward |

### 5.2 Snapshot composition

{chr(10).join(dataset_table_lines)}

![Dataset token budget](assets/{args.snapshot}/dataset_token_budget.svg)

### 5.3 Example rows

#### SFT example

```json
{short_json_block(sft_example, ['scenario_id', 'tags', 'prompt', 'completion'])}
```

#### DPO example

```json
{short_json_block(dpo_example, ['scenario_id', 'prompt', 'chosen', 'rejected'])}
```

#### Reward-model pointwise example

```json
{short_json_block(rm_example, ['scenario_id', 'prompt', 'response', 'label', 'score'])}
```

#### PPO prompt example

```json
{short_json_block(ppo_example, ['scenario_id', 'prompt', 'reference_reply'])}
```

#### GRPO prompt example

```json
{short_json_block(grpo_example, ['scenario_id', 'prompt', 'candidate_reply', 'reward_components'])}
```

## 6. Training Pipeline

### 6.1 Frozen lineage

The actual staged pipeline on the H200 was:

1. freeze the `20260418_2m_snapshot` dataset
2. train a classical reward model (`distilroberta-base`)
3. train full-weight SFT on `SmolLM2-135M-Instruct`
4. train DPO on top of the same model family
5. branch into:
   - GRPO using the DPO-initialized policy
   - PPO reward modeling using a SmolLM-based reward head
   - PPO using the DPO-initialized policy + PPO reward model

### 6.2 Reproduction commands

```bash
# Snapshot prep
python3 love_game/build_training_splits.py --snapshot 20260418_2m_snapshot

# SFT
python3 love_game/run_sft_full.py \\
  --train-dataset love_game/splits/20260418_2m_snapshot/sft_train.jsonl \\
  --eval-dataset love_game/splits/20260418_2m_snapshot/sft_validation.jsonl \\
  --output-dir love_game/checkpoints/20260418_2m_snapshot/smol_135m_sft_v3

# DPO
python3 love_game/run_dpo_full.py \\
  --train-dataset love_game/splits/20260418_2m_snapshot/dpo_train.jsonl \\
  --eval-dataset love_game/splits/20260418_2m_snapshot/dpo_validation.jsonl \\
  --output-dir love_game/checkpoints/20260418_2m_snapshot/smol_135m_sft_dpo_v2

# GRPO
python3 love_game/run_grpo.py \\
  --train-dataset love_game/splits/20260418_2m_snapshot/grpo_train.jsonl \\
  --eval-dataset love_game/splits/20260418_2m_snapshot/grpo_validation.jsonl \\
  --reward-model love_game/checkpoints/20260418_2m_snapshot/reward_model_v2 \\
  --output-dir love_game/checkpoints/20260418_2m_snapshot/smol_135m_sft_dpo_grpo_v1

# PPO reward model
python3 love_game/run_reward_model_ppo.py \\
  --train-dataset love_game/splits/20260418_2m_snapshot/dpo_train.jsonl \\
  --eval-dataset love_game/splits/20260418_2m_snapshot/dpo_validation.jsonl \\
  --output-dir love_game/checkpoints/20260418_2m_snapshot/reward_model_ppo_v1

# PPO
python3 love_game/run_ppo.py \\
  --train-dataset love_game/splits/20260418_2m_snapshot/ppo_train.jsonl \\
  --eval-dataset love_game/splits/20260418_2m_snapshot/ppo_validation.jsonl \\
  --reward-model love_game/checkpoints/20260418_2m_snapshot/reward_model_ppo_v1 \\
  --output-dir love_game/checkpoints/20260418_2m_snapshot/smol_135m_sft_dpo_ppo_v1
```

## 7. Training Techniques, Explained for Students

### 7.1 SFT

SFT is the simplest thing here. It says:

> “Here is the prompt. Here is the reply we want. Copy that pattern.”

That is why SFT data is a direct prompt/completion dataset.

Relevant implementation:

```python
{code_snippet(LOVE_DIR / 'run_sft_full.py', 93, 155)}
```

### 7.2 DPO

DPO does **not** need a separate reward model.  
It only needs pairs:

- one better answer (`chosen`)
- one worse answer (`rejected`)

It asks the model to increase the probability of the chosen answer relative to the rejected one.

Relevant implementation:

```python
{code_snippet(LOVE_DIR / 'run_dpo_full.py', 60, 109)}
```

### 7.3 Classical reward model

Here we explicitly train a scorer:

> `prompt + reply -> how good is this?`

This is the most direct “reward model” in the usual RLHF sense.

Relevant implementation:

```python
{code_snippet(LOVE_DIR / 'run_reward_model_ppo.py', 50, 95)}
```

### 7.4 GRPO

GRPO is an online RL method. The policy samples completions, the system scores them, and the model is nudged toward better grouped samples.

In this project the reward was a **mixture** of:

- a learned reward model
- a rule-based “Love Game” reward

Relevant implementation:

```python
{code_snippet(LOVE_DIR / 'run_grpo.py', 109, 184)}
```

### 7.5 PPO

PPO is the classic RLHF-shaped story:

- a policy model
- a reference model
- a value model
- a reward model
- online rollouts

Relevant implementation:

```python
{code_snippet(LOVE_DIR / 'run_ppo.py', 70, 147)}
```

### 7.6 RLHF vs RLVR vs GRPO in plain language

```mermaid
flowchart TD
    A["SFT"] --> B["Preference Optimization (DPO)"]
    B --> C["Reward Modeling"]
    C --> D["PPO"]
    B --> E["GRPO"]
    F["Rule / Verifier Reward"] --> E
    G["Human Preference Pairs"] --> B
    G --> C
```

- **RLHF** is the umbrella idea: teach from preferences or rewards that try to represent human judgment.
- **DPO** is preference optimization without online rollout training.
- **PPO** is online RL with a learned reward signal.
- **GRPO** is grouped online RL; it can be easier to use when you have mixed reward sources.
- **RLVR** is strongest when a verifier can check correctness directly. Love Game is only **partly verifiable**, so it lives in the messy middle.

## 8. Results Overview

{chr(10).join(summary_table_lines)}

## 9. Stage-by-Stage Curves

### 9.1 SFT

![SFT loss curve](assets/{args.snapshot}/sft_loss_curve.svg)

Interpretation:

- the eval loss came down to `3.3744`
- the curve proved the full-weight SFT path worked
- the model became more anchored, but still sounded tiny and repetitive

### 9.2 Reward Model v2 (DistilRoBERTa)

![Reward model v2](assets/{args.snapshot}/reward_model_v2_curve.svg)

Interpretation:

- final `eval_accuracy = 0.4588`
- this reward model was **real**, but not yet good enough to be a trustworthy standalone judge
- that result is useful pedagogically because it shows how reward-model quality can lag behind the ambition of the RL setup

### 9.3 DPO

![DPO curve](assets/{args.snapshot}/dpo_curve.svg)

Interpretation:

- final `eval_loss = 0.2334`
- DPO was the cleanest and strongest improvement after SFT
- the preference objective fit this synthetic character task well

### 9.4 GRPO

![GRPO reward curve](assets/{args.snapshot}/grpo_rewards.svg)

![GRPO step time](assets/{args.snapshot}/grpo_step_time.svg)

Interpretation:

- final `eval_loss = 9.8005e-10`
- GRPO mixed:
  - learned reward model mean
  - rule reward mean
- the fast run was intentionally shortened for time, but it proved the GRPO loop worked on the tiny policy

### 9.5 PPO-Compatible Reward Model

![PPO reward model curve](assets/{args.snapshot}/reward_model_ppo_curve.svg)

Interpretation:

- final `eval_loss = 2.1098e-05`
- unlike the DistilRoBERTa reward model, this one was shaped to fit the PPO stack more directly

### 9.6 PPO

![PPO reward curve](assets/{args.snapshot}/ppo_reward_curve.svg)

Interpretation:

- the PPO run finished a short **64-episode / 16-step** demo cycle
- it did not emit a separate `final_metrics.json` because the configured eval interval was longer than the full run
- the trainer state still proves the run completed:
  - `episode = {ppo_state['episode']}`
  - `global_step = {ppo_state['global_step']}`
  - `last RLHF reward = {ppo_state['log_history'][-1]['objective/rlhf_reward']:.4f}`
  - `last score = {ppo_state['log_history'][-1]['objective/scores']:.4f}`

## 10. Sample Outputs Across the Lineage

All sample generations were run against the same validation-style conversational scenarios.

{chr(10).join(sample_comparison_lines)}

### 10.1 One shared scenario, five different models

#### Reference answer

```text
{sample_sets['sft']['reference'][:1200]}
```

#### Base model

```text
{sample_sets['base']['generated'][:1000]}
```

#### SFT

```text
{sample_sets['sft']['generated'][:1000]}
```

#### DPO

```text
{sample_sets['dpo']['generated'][:1000]}
```

#### GRPO

```text
{sample_sets['grpo']['generated'][:1000]}
```

#### PPO

```text
{sample_sets['ppo']['generated'][:1000]}
```

## 11. What Worked

1. The entire pipeline was made concrete: dataset generation, split freezing, SFT, DPO, reward modeling, GRPO, and PPO all existed as runnable code.
2. The `135M` model could absolutely absorb the **Aditi** style to a noticeable degree.
3. DPO was especially effective for this small, stylized task.
4. Both GRPO and PPO were not just theory; they completed actual runs on the H200.
5. The project created a strong teaching story about:
   - how datasets differ by method
   - why reward models matter
   - why RLHF is a family of methods, not one algorithm

## 12. What Did Not Work Perfectly

1. The first reward model was weak (`eval_accuracy ≈ 0.46`), which means it should not be treated as a ground-truth judge.
2. The PPO run was intentionally short and should be treated as a **working demonstration**, not a fully converged result.
3. The `135M` model still lacked enough capacity to become deeply convincing over long conversations.
4. The larger dataset growth phase improved things, but this project still used a relatively small final frozen snapshot for a full RLHF-style stack.
5. Some earlier notes in the repo described PPO/GRPO as “not yet run”; those were true earlier in the night but are now superseded by this report.

## 13. Practical Conclusions

If I had to summarize the project in one sentence for a talk:

> A tiny instruct model can be pushed surprisingly far with staged post-training, but the jump from “better” to “convincing” is bottlenecked more by reward quality and model capacity than by the choice of acronym.

Best takeaways:

- **SFT** gets the style into the model.
- **DPO** is a great next step when you can generate chosen/rejected pairs.
- **Reward modeling** is necessary for PPO-style RLHF, but it is easy to overestimate how good your reward model is.
- **GRPO** is attractive when you can mix learned and rule-based rewards.
- **PPO** is powerful, but it adds moving parts very quickly.

## 14. Artifacts and Links

### 14.1 Hugging Face

- Dataset backup: [{HF_DATASET_REPO}]({HF_DATASET_REPO})
- Model suite: [{HF_MODEL_REPO}]({HF_MODEL_REPO})
- Report/docs bundle: [{model_subpaths['docs']}]({model_subpaths['docs']})
- Metrics bundle: [{model_subpaths['metrics']}]({model_subpaths['metrics']})
- Sample generations: [{model_subpaths['samples']}]({model_subpaths['samples']})
- Base policy model: [{BASE_MODEL_LINK}]({BASE_MODEL_LINK})
- Reward-model base: [{REWARD_MODEL_BASE_LINK}]({REWARD_MODEL_BASE_LINK})

### 14.2 Local artifact map

| Artifact | Path |
|---|---|
| Deep report | `love_game/reports/LOVE_GAME_DEEP_REPORT.md` |
| Plot assets | `love_game/reports/assets/{args.snapshot}/` |
| Final checkpoint backup | `love_game/local_backups/{args.snapshot}/` |
| Snapshot logs | `love_game/local_backups/{args.snapshot}_logs/` |
| Sample generations | `love_game/remote_samples/{args.snapshot}/` |

### 14.3 Checkpoint names

- [`reward_model_v2`]({model_subpaths['reward_model_v2']})
- [`smol_135m_sft_v3`]({model_subpaths['smol_135m_sft_v3']})
- [`smol_135m_sft_dpo_v2`]({model_subpaths['smol_135m_sft_dpo_v2']})
- [`smol_135m_sft_dpo_grpo_v1`]({model_subpaths['smol_135m_sft_dpo_grpo_v1']})
- [`reward_model_ppo_v1`]({model_subpaths['reward_model_ppo_v1']})
- [`smol_135m_sft_dpo_ppo_v1`]({model_subpaths['smol_135m_sft_dpo_ppo_v1']})

## 15. Final Notes for Tomorrow’s Presentation

If I were presenting this to students, I would say:

1. Start with the base model and show that it is weak and generic.
2. Show SFT data and say: “This is imitation.”
3. Show DPO data and say: “This is preference learning.”
4. Show reward-model data and say: “This is how we try to teach a judge.”
5. Show PPO/GRPO and say: “Now the model generates, gets scored, and learns from the score.”
6. End with the philosophical punchline:
   - verification is easy for math/code
   - much harder for affection, warmth, tone, and understanding
   - Love Game lives exactly in that messy middle

That is what makes it a good teaching project.
"""

    report_path = report_dir / "LOVE_GAME_DEEP_REPORT.md"
    report_path.write_text(report, encoding="utf-8")
    print(report_path)


if __name__ == "__main__":
    main()
