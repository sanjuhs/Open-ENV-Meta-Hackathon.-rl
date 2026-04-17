#!/usr/bin/env python3
"""Train a tiny pure-Python reward model on Love Game preference data."""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from love_game.common import DATASETS_DIR, read_jsonl


TOKEN_RE = re.compile(r"[a-zA-Z']+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1 / (1 + z)
    z = math.exp(x)
    return z / (1 + z)


def text_to_features(text: str, vocab: dict[str, int]) -> dict[int, float]:
    counts = Counter(tokenize(text))
    return {vocab[token]: float(count) for token, count in counts.items() if token in vocab}


def score_features(features: dict[int, float], weights: list[float], bias: float) -> float:
    total = bias
    for idx, value in features.items():
        total += weights[idx] * value
    return total


def predict_prob(text: str, vocab: dict[str, int], weights: list[float], bias: float) -> float:
    return sigmoid(score_features(text_to_features(text, vocab), weights, bias))


def build_vocab(rows: list[dict], max_features: int) -> dict[str, int]:
    counts = Counter()
    for row in rows:
        counts.update(tokenize(row["prompt"]))
        counts.update(tokenize(row["response"]))
    return {token: idx for idx, (token, _) in enumerate(counts.most_common(max_features))}


def make_examples(rows: list[dict]) -> list[dict]:
    return [
        {
            "text": f"{row['prompt']} {row['response']}",
            "label": int(row["label"]),
        }
        for row in rows
    ]


def train_model(
    train_rows: list[dict],
    *,
    max_features: int,
    epochs: int,
    learning_rate: float,
) -> tuple[dict[str, int], list[float], float]:
    vocab = build_vocab(train_rows, max_features=max_features)
    weights = [0.0] * len(vocab)
    bias = 0.0
    examples = make_examples(train_rows)

    for epoch in range(epochs):
        random.shuffle(examples)
        total_loss = 0.0
        for example in examples:
            features = text_to_features(example["text"], vocab)
            logit = score_features(features, weights, bias)
            prob = sigmoid(logit)
            error = prob - example["label"]
            total_loss += -(
                example["label"] * math.log(max(prob, 1e-8))
                + (1 - example["label"]) * math.log(max(1 - prob, 1e-8))
            )
            for idx, value in features.items():
                weights[idx] -= learning_rate * error * value
            bias -= learning_rate * error
        avg_loss = total_loss / max(1, len(examples))
        print(f"epoch={epoch + 1} avg_loss={avg_loss:.4f}")
    return vocab, weights, bias


def accuracy(rows: list[dict], vocab: dict[str, int], weights: list[float], bias: float) -> float:
    if not rows:
        return 0.0
    correct = 0
    for row in rows:
        prob = predict_prob(f"{row['prompt']} {row['response']}", vocab, weights, bias)
        pred = 1 if prob >= 0.5 else 0
        if pred == int(row["label"]):
            correct += 1
    return correct / len(rows)


def pairwise_accuracy(rows: list[dict], vocab: dict[str, int], weights: list[float], bias: float) -> float:
    if not rows:
        return 0.0
    correct = 0
    for row in rows:
        chosen = predict_prob(f"{row['prompt']} {row['preferred_response']}", vocab, weights, bias)
        rejected = predict_prob(f"{row['prompt']} {row['dispreferred_response']}", vocab, weights, bias)
        if chosen > rejected:
            correct += 1
    return correct / len(rows)


def top_tokens(weights: list[float], vocab: dict[str, int], limit: int = 20) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
    reverse_vocab = {idx: token for token, idx in vocab.items()}
    scored = [(reverse_vocab[idx], weight) for idx, weight in enumerate(weights)]
    positives = sorted(scored, key=lambda item: item[1], reverse=True)[:limit]
    negatives = sorted(scored, key=lambda item: item[1])[:limit]
    return positives, negatives


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-path", type=Path, default=DATASETS_DIR / "rm_pointwise_train.jsonl")
    parser.add_argument("--pairwise-path", type=Path, default=DATASETS_DIR / "rlhf_pairs_train.jsonl")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "love_game" / "models")
    parser.add_argument("--max-features", type=int, default=2500)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--learning-rate", type=float, default=0.06)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    rows = read_jsonl(args.train_path)
    if not rows:
        raise RuntimeError(f"No rows found in {args.train_path}")
    rng.shuffle(rows)
    split_at = max(1, int(len(rows) * 0.8))
    train_rows = rows[:split_at]
    eval_rows = rows[split_at:]
    pairwise_rows = read_jsonl(args.pairwise_path)

    vocab, weights, bias = train_model(
        train_rows,
        max_features=args.max_features,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
    )

    train_acc = accuracy(train_rows, vocab, weights, bias)
    eval_acc = accuracy(eval_rows, vocab, weights, bias)
    pair_acc = pairwise_accuracy(pairwise_rows, vocab, weights, bias)
    positives, negatives = top_tokens(weights, vocab)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.output_dir / "reward_model.json"
    report_path = args.output_dir / "reward_model_report.md"

    model_path.write_text(
        json.dumps(
            {
                "bias": bias,
                "vocab": vocab,
                "weights": weights,
                "train_examples": len(train_rows),
                "eval_examples": len(eval_rows),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    report = f"""# Love Game Reward Model Report

- Train examples: {len(train_rows)}
- Eval examples: {len(eval_rows)}
- Pairwise preference examples: {len(pairwise_rows)}
- Train accuracy: {train_acc:.4f}
- Eval accuracy: {eval_acc:.4f}
- Pairwise preference accuracy: {pair_acc:.4f}

## Strong Positive Tokens

{chr(10).join(f"- `{token}`: {weight:.4f}" for token, weight in positives)}

## Strong Negative Tokens

{chr(10).join(f"- `{token}`: {weight:.4f}" for token, weight in negatives)}
"""
    report_path.write_text(report, encoding="utf-8")

    print(f"Saved reward model to {model_path}")
    print(f"Saved report to {report_path}")
    print(f"train_accuracy={train_acc:.4f}")
    print(f"eval_accuracy={eval_acc:.4f}")
    print(f"pairwise_accuracy={pair_acc:.4f}")


if __name__ == "__main__":
    main()
