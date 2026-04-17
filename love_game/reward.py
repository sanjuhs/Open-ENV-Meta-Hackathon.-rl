"""Simple rule-based reward helpers for Love Game."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict


WARM_WORDS = {
    "sorry",
    "okay",
    "listen",
    "hear you",
    "with you",
    "hug",
    "proud",
    "sweet",
    "cute",
    "walk",
    "ice cream",
    "okay fine",
}

BLAND_PATTERNS = {
    "i understand",
    "as an ai",
    "how can i help you",
    "i'm sorry to hear that",
}

CHARACTER_MARKERS = {
    "bangalore",
    "metro",
    "jayanagar",
    "whitefield",
    "dosa",
    "ice cream",
    "fuck",
}


@dataclass
class RewardBreakdown:
    warmth: float
    character_consistency: float
    blandness_penalty: float
    contradiction_penalty: float
    total: float

    def to_dict(self) -> dict:
        return asdict(self)


def score_reply(reply: str) -> RewardBreakdown:
    lowered = reply.lower()

    warmth = sum(0.15 for token in WARM_WORDS if token in lowered)
    consistency = sum(0.1 for token in CHARACTER_MARKERS if token in lowered)
    blandness_penalty = sum(0.2 for token in BLAND_PATTERNS if token in lowered)

    contradiction_penalty = 0.0
    if "i never swear" in lowered:
        contradiction_penalty += 0.5
    if "i hate walking" in lowered:
        contradiction_penalty += 0.5

    total = warmth + consistency - blandness_penalty - contradiction_penalty
    return RewardBreakdown(
        warmth=round(warmth, 4),
        character_consistency=round(consistency, 4),
        blandness_penalty=round(blandness_penalty, 4),
        contradiction_penalty=round(contradiction_penalty, 4),
        total=round(total, 4),
    )


def compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
