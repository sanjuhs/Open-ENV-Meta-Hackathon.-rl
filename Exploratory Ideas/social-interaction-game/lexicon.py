from __future__ import annotations

import re
from typing import Iterable, List, Set

from vad_lexicon import load_vad_lexicon


VAD_LEXICON = load_vad_lexicon()


STOPWORDS: Set[str] = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "do",
    "for",
    "from",
    "had",
    "has",
    "have",
    "i",
    "if",
    "in",
    "is",
    "it",
    "just",
    "me",
    "my",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "them",
    "they",
    "this",
    "to",
    "too",
    "we",
    "with",
    "you",
    "your",
    "right",
    "now",
    "really",
}

EMPATHY_MARKERS: List[str] = [
    "i'm sorry",
    "i am sorry",
    "that sounds hard",
    "that sounds brutal",
    "that sounds painful",
    "that sounds rough",
    "i hear you",
    "i get why",
    "that makes sense",
    "i'm here",
    "i am here",
    "you don't have to",
    "you do not have to",
    "i can see",
    "i know this hurts",
]

ADVICE_MARKERS: List[str] = [
    "you should",
    "you need to",
    "why don't you",
    "why dont you",
    "try to",
    "my advice",
    "the best thing to do",
    "you have to",
    "go do",
]

POSITIVE_WORDS = {
    "proud": 2.0,
    "love": 2.0,
    "good": 1.0,
    "glad": 1.5,
    "warm": 1.0,
    "safe": 1.2,
    "together": 1.2,
    "gentle": 1.3,
    "here": 0.8,
    "support": 1.8,
    "supportive": 1.8,
    "care": 1.5,
    "caring": 1.6,
    "proudly": 1.8,
    "sweet": 1.2,
    "brave": 1.3,
    "okay": 1.0,
}

NEGATIVE_WORDS = {
    "stupid": 2.5,
    "dramatic": 2.0,
    "lazy": 2.2,
    "crazy": 2.2,
    "overreacting": 2.3,
    "whatever": 1.8,
    "deal": 1.2,
    "fine": 0.5,
    "calm": 0.0,
    "numb": 0.8,
    "fired": 1.7,
    "fight": 1.5,
    "upset": 1.7,
    "angry": 2.0,
}

CALMING_WORDS = {
    "breathe",
    "slow",
    "pause",
    "rest",
    "here",
    "with",
    "gentle",
    "tonight",
    "moment",
    "minute",
    "space",
}

HIGH_AROUSAL_WORDS = {
    "immediately",
    "urgent",
    "fix",
    "now",
    "tonight",
    "panic",
    "wild",
    "huge",
    "right away",
}

ASSERTIVE_WORDS = {
    "will",
    "can",
    "let's",
    "lets",
    "together",
}

HEDGING_WORDS = {
    "maybe",
    "perhaps",
    "sort of",
    "kind of",
}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z']+", text.lower())


def content_tokens(text: str) -> List[str]:
    return [token for token in tokenize(text) if token not in STOPWORDS and len(token) > 2]


def contains_any_phrase(text: str, phrases: Iterable[str]) -> bool:
    normalized = normalize_text(text)
    return any(phrase in normalized for phrase in phrases)


def count_phrase_hits(text: str, phrases: Iterable[str]) -> int:
    normalized = normalize_text(text)
    return sum(1 for phrase in phrases if phrase in normalized)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def overlap_ratio(left_tokens: List[str], right_tokens: List[str]) -> float:
    left = set(left_tokens)
    right = set(right_tokens)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left)


def estimate_vad(text: str) -> dict:
    tokens = tokenize(text)
    if not tokens:
        return {"valence": 0.5, "arousal": 0.5, "dominance": 0.5}

    vad_hits = [VAD_LEXICON[token] for token in tokens if token in VAD_LEXICON]
    positive = sum(POSITIVE_WORDS.get(token, 0.0) for token in tokens)
    negative = sum(NEGATIVE_WORDS.get(token, 0.0) for token in tokens)
    calming = sum(1.0 for token in tokens if token in CALMING_WORDS)
    high_arousal = sum(1.0 for token in tokens if token in HIGH_AROUSAL_WORDS)
    assertive = sum(1.0 for token in tokens if token in ASSERTIVE_WORDS)
    hedging = sum(1.0 for token in tokens if token in HEDGING_WORDS)

    exclamations = text.count("!")
    questions = text.count("?")

    if vad_hits:
        valence = sum(hit[0] for hit in vad_hits) / len(vad_hits)
        arousal = sum(hit[1] for hit in vad_hits) / len(vad_hits)
        dominance = sum(hit[2] for hit in vad_hits) / len(vad_hits)
    else:
        valence = 0.5
        arousal = 0.42
        dominance = 0.5

    valence = clamp(valence + 0.03 * positive - 0.04 * negative)
    arousal = clamp(arousal + 0.05 * high_arousal - 0.04 * calming + 0.04 * exclamations + 0.02 * questions)
    dominance = clamp(dominance + 0.03 * assertive - 0.03 * hedging)

    return {
        "valence": round(valence, 3),
        "arousal": round(arousal, 3),
        "dominance": round(dominance, 3),
    }
