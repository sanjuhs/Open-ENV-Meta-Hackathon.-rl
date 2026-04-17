#!/usr/bin/env python3
"""Turn Hugging Face trainer logs into JSON summaries and a simple SVG chart."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def extract_points(log_history: list[dict], key: str) -> list[tuple[float, float]]:
    points = []
    for item in log_history:
        if key in item and "step" in item:
            points.append((float(item["step"]), float(item[key])))
    return points


def svg_line_chart(train_points: list[tuple[float, float]], eval_points: list[tuple[float, float]], width: int = 900, height: int = 420) -> str:
    all_points = train_points + eval_points
    if not all_points:
        return "<svg xmlns='http://www.w3.org/2000/svg' width='900' height='420'></svg>"

    min_x = min(point[0] for point in all_points)
    max_x = max(point[0] for point in all_points)
    min_y = min(point[1] for point in all_points)
    max_y = max(point[1] for point in all_points)
    if max_x == min_x:
        max_x += 1
    if max_y == min_y:
        max_y += 1

    pad = 40

    def scale_x(x: float) -> float:
        return pad + (x - min_x) / (max_x - min_x) * (width - pad * 2)

    def scale_y(y: float) -> float:
        return height - pad - (y - min_y) / (max_y - min_y) * (height - pad * 2)

    def path(points: list[tuple[float, float]]) -> str:
        if not points:
            return ""
        return " ".join(
            ("M" if idx == 0 else "L") + f"{scale_x(x):.2f},{scale_y(y):.2f}"
            for idx, (x, y) in enumerate(points)
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
  <rect width="100%" height="100%" fill="#faf7f0"/>
  <line x1="{pad}" y1="{height-pad}" x2="{width-pad}" y2="{height-pad}" stroke="#8b7b67"/>
  <line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height-pad}" stroke="#8b7b67"/>
  <path d="{path(train_points)}" fill="none" stroke="#aa4e29" stroke-width="3"/>
  <path d="{path(eval_points)}" fill="none" stroke="#2e6a57" stroke-width="3"/>
  <text x="{pad}" y="24" font-size="18" fill="#2f241b">Training vs Eval Loss</text>
  <text x="{width-220}" y="30" font-size="14" fill="#aa4e29">train_loss</text>
  <text x="{width-120}" y="30" font-size="14" fill="#2e6a57">eval_loss</text>
</svg>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trainer-state", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    state = json.loads(args.trainer_state.read_text(encoding="utf-8"))
    log_history = state.get("log_history", [])
    train_points = extract_points(log_history, "loss")
    eval_points = extract_points(log_history, "eval_loss")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "loss_points.json").write_text(
        json.dumps(
            {
                "train_loss": train_points,
                "eval_loss": eval_points,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (args.output_dir / "loss_chart.svg").write_text(
        svg_line_chart(train_points, eval_points),
        encoding="utf-8",
    )
    print(f"Wrote {(args.output_dir / 'loss_points.json')}")
    print(f"Wrote {(args.output_dir / 'loss_chart.svg')}")


if __name__ == "__main__":
    main()
