from __future__ import annotations

from typing import Dict, List, Tuple

from lexicon import (
    ADVICE_MARKERS,
    EMPATHY_MARKERS,
    contains_any_phrase,
    content_tokens,
    count_phrase_hits,
    estimate_vad,
    normalize_text,
    overlap_ratio,
)
from models import Scenario, ScoreDetail


WEIGHTS: Dict[str, float] = {
    "acknowledgement": 0.15,
    "relevance": 0.12,
    "empathy": 0.14,
    "advice_policy": 0.10,
    "question_balance": 0.07,
    "length": 0.06,
    "quantity": 0.06,
    "manner": 0.06,
    "consistency": 0.10,
    "boundary_respect": 0.10,
    "emotional_alignment": 0.14,
}
TOTAL_WEIGHT = sum(WEIGHTS.values())


def _score_from_range(value: int, low: int, high: int) -> float:
    if low <= value <= high:
        return 1.0
    if value < low:
        gap = low - value
    else:
        gap = value - high
    return max(0.0, 1.0 - 0.12 * gap)


def _banded_range_score(value: float, low: float, high: float) -> float:
    if low <= value <= high:
        return 1.0
    gap = min(abs(value - low), abs(value - high))
    return max(0.0, 1.0 - (gap / 0.35))


def _check_acknowledgement(user_message: str, response: str, required_topics: List[str]) -> Tuple[float, bool, str]:
    normalized = normalize_text(response)
    message_tokens = content_tokens(user_message)
    response_tokens = content_tokens(response)
    overlap = overlap_ratio(message_tokens, response_tokens)
    required_hit = any(topic.lower() in normalized for topic in required_topics) if required_topics else False
    empathy_hit = count_phrase_hits(response, EMPATHY_MARKERS) > 0

    passed = required_hit or overlap >= 0.15 or empathy_hit
    if required_hit or overlap >= 0.15:
        score = 1.0
    elif empathy_hit:
        score = 0.7
    else:
        score = min(0.4, overlap * 2)
    if passed:
        reason = "Response acknowledges the user's situation before drifting."
    else:
        reason = "Response barely references the user's actual message."
    return score, passed, reason


def _check_relevance(user_message: str, response: str, minimum_overlap: float) -> Tuple[float, bool, str]:
    overlap = overlap_ratio(content_tokens(user_message), content_tokens(response))
    empathy_hit = count_phrase_hits(response, EMPATHY_MARKERS) > 0
    if overlap >= minimum_overlap:
        score = min(1.0, overlap / max(minimum_overlap, 0.01))
        passed = True
        reason = f"Topic overlap is solid ({overlap:.2f})."
    elif empathy_hit:
        score = 0.65
        passed = True
        reason = "Response stays emotionally on-topic even without repeating the same words."
    else:
        score = min(1.0, overlap / max(minimum_overlap, 0.01))
        passed = False
        reason = f"Topic overlap is weak ({overlap:.2f})."
    if passed and overlap >= minimum_overlap:
        return score, passed, reason
    if passed:
        return score, passed, reason
    return score, passed, reason


def _check_empathy(response: str, minimum_markers: int) -> Tuple[float, bool, str]:
    hits = count_phrase_hits(response, EMPATHY_MARKERS)
    passed = hits >= minimum_markers
    score = min(1.0, hits / max(minimum_markers, 1))
    if passed:
        reason = f"Empathy markers detected ({hits})."
    else:
        reason = "Little explicit empathy was detected."
    return score, passed, reason


def _check_advice_policy(response: str, allow_advice: bool) -> Tuple[float, bool, str]:
    has_advice = contains_any_phrase(response, ADVICE_MARKERS)
    if allow_advice:
        return (1.0, True, "Advice is allowed in this scenario.")
    if has_advice:
        return (0.0, False, "Response gives advice where the scenario asks for restraint.")
    return (1.0, True, "Response avoids unsolicited advice.")


def _check_question_balance(response: str, max_questions: int) -> Tuple[float, bool, str]:
    question_count = response.count("?")
    passed = question_count <= max_questions
    score = 1.0 if passed else max(0.0, 1.0 - 0.4 * (question_count - max_questions))
    if passed:
        reason = f"Question count is within range ({question_count})."
    else:
        reason = f"Too many questions ({question_count}) for this emotional context."
    return score, passed, reason


def _check_length(response: str, preferred_length: Tuple[int, int]) -> Tuple[float, bool, str]:
    words = len(response.split())
    low, high = preferred_length
    score = _score_from_range(words, low, high)
    passed = score >= 0.75
    if passed:
        reason = f"Length fits the persona preference ({words} words)."
    else:
        reason = f"Length misses the preferred range ({words} words, target {low}-{high})."
    return score, passed, reason


def _check_quantity(user_message: str, response: str, ratio_range: Tuple[float, float]) -> Tuple[float, bool, str]:
    user_words = max(1, len(user_message.split()))
    response_words = len(response.split())
    ratio = response_words / user_words
    low, high = ratio_range
    if low <= ratio <= high:
        return (1.0, True, f"Response quantity fits the conversational load ({ratio:.2f}x input length).")
    gap = min(abs(ratio - low), abs(ratio - high))
    score = max(0.0, 1.0 - (gap / 1.5))
    return (score, score >= 0.7, f"Response quantity is off ({ratio:.2f}x input length).")


def _check_manner(response: str, max_sentences: int, max_exclamations: int) -> Tuple[float, bool, str]:
    sentence_count = max(1, response.count(".") + response.count("!") + response.count("?"))
    exclamations = response.count("!")
    uppercase_ratio = sum(1 for char in response if char.isupper()) / max(1, sum(1 for char in response if char.isalpha()))
    repeated_punct = "!!" in response or "??" in response or "..." in response

    penalties = 0
    if sentence_count > max_sentences:
        penalties += 1
    if exclamations > max_exclamations:
        penalties += 1
    if uppercase_ratio > 0.35:
        penalties += 1
    if repeated_punct:
        penalties += 1

    score = max(0.0, 1.0 - 0.25 * penalties)
    passed = score >= 0.75
    if passed:
        reason = "Response is clear and controlled."
    else:
        reason = "Response style is noisy or harder to process than this situation wants."
    return score, passed, reason


def _check_boundary_respect(response: str, banned_topics: List[str]) -> Tuple[float, bool, str]:
    normalized = normalize_text(response)
    matches = [topic for topic in banned_topics if topic.lower() in normalized]
    if matches:
        return (0.0, False, f"Response revisits banned content: {', '.join(matches)}.")
    return (1.0, True, "Response respects stated boundaries.")


def _check_consistency(response: str, history: List[dict], banned_topics: List[str]) -> Tuple[float, bool, str]:
    prior_assistant_messages = [item["text"] for item in history if item["role"] == "assistant"]
    if not prior_assistant_messages:
        return (1.0, True, "No prior assistant turns to contradict.")

    normalized_response = normalize_text(response)
    prior_normalized = [normalize_text(message) for message in prior_assistant_messages]
    made_non_pressure_commitment = any(
        ("won't push" in message or "will not push" in message or "no pressure" in message or "take your time" in message)
        for message in prior_normalized
    )
    violates_boundary_now = any(topic.lower() in normalized_response for topic in banned_topics) or contains_any_phrase(response, ADVICE_MARKERS)

    if made_non_pressure_commitment and violates_boundary_now:
        return (0.0, False, "Response contradicts an earlier low-pressure commitment.")

    repeated_message = any(normalized_response == message for message in prior_normalized)
    if repeated_message:
        return (0.45, False, "Response repeats itself instead of advancing the interaction.")

    return (1.0, True, "Response is consistent with the prior assistant behavior.")


def _check_emotional_alignment(
    user_message: str,
    response: str,
    valence_range: Tuple[float, float],
    arousal_range: Tuple[float, float],
    dominance_range: Tuple[float, float],
) -> Tuple[float, bool, str, dict]:
    user_vad = estimate_vad(user_message)
    vad = estimate_vad(response)
    valence_score = _banded_range_score(vad["valence"], *valence_range)
    arousal_score = _banded_range_score(vad["arousal"], *arousal_range)
    dominance_score = _banded_range_score(vad["dominance"], *dominance_range)

    trajectory_score = 1.0
    if user_vad["valence"] < 0.40 and vad["arousal"] > user_vad["arousal"] + 0.15:
        trajectory_score -= 0.35
    if user_vad["valence"] > 0.65 and abs(vad["arousal"] - user_vad["arousal"]) > 0.35:
        trajectory_score -= 0.20
    if user_vad["dominance"] < 0.35 and vad["dominance"] > 0.80:
        trajectory_score -= 0.20

    score = (valence_score + arousal_score + dominance_score + max(0.0, trajectory_score)) / 4
    passed = score >= 0.75
    if passed:
        reason = (
            "Estimated emotional tone fits target V/A/D: "
            f"{vad['valence']:.2f}/{vad['arousal']:.2f}/{vad['dominance']:.2f}."
        )
    else:
        reason = (
            "Estimated emotional tone misses target V/A/D: "
            f"{vad['valence']:.2f}/{vad['arousal']:.2f}/{vad['dominance']:.2f}."
        )
    return score, passed, reason, {"response": vad, "user": user_vad, "trajectory_score": round(max(0.0, trajectory_score), 3)}


def score_response(scenario: Scenario, user_message: str, response: str, history: List[dict] | None = None) -> Tuple[float, List[ScoreDetail], dict]:
    rules = scenario.rules
    details: List[ScoreDetail] = []
    metadata: dict = {}
    history = history or []

    score, passed, reason = _check_acknowledgement(user_message, response, rules.required_topics)
    details.append(ScoreDetail("acknowledgement", score, WEIGHTS["acknowledgement"], passed, reason))

    score, passed, reason = _check_relevance(user_message, response, rules.min_relevance_overlap)
    details.append(ScoreDetail("relevance", score, WEIGHTS["relevance"], passed, reason))

    score, passed, reason = _check_empathy(response, rules.min_empathy_markers)
    details.append(ScoreDetail("empathy", score, WEIGHTS["empathy"], passed, reason))

    score, passed, reason = _check_advice_policy(response, rules.allow_advice)
    details.append(ScoreDetail("advice_policy", score, WEIGHTS["advice_policy"], passed, reason))

    score, passed, reason = _check_question_balance(response, rules.max_questions)
    details.append(ScoreDetail("question_balance", score, WEIGHTS["question_balance"], passed, reason))

    score, passed, reason = _check_length(response, rules.preferred_length)
    details.append(ScoreDetail("length", score, WEIGHTS["length"], passed, reason))

    score, passed, reason = _check_quantity(user_message, response, rules.quantity_ratio_range)
    details.append(ScoreDetail("quantity", score, WEIGHTS["quantity"], passed, reason))

    score, passed, reason = _check_manner(response, rules.max_sentences, rules.max_exclamations)
    details.append(ScoreDetail("manner", score, WEIGHTS["manner"], passed, reason))

    score, passed, reason = _check_consistency(response, history, rules.banned_topics)
    details.append(ScoreDetail("consistency", score, WEIGHTS["consistency"], passed, reason))

    score, passed, reason = _check_boundary_respect(response, rules.banned_topics)
    details.append(ScoreDetail("boundary_respect", score, WEIGHTS["boundary_respect"], passed, reason))

    score, passed, reason, vad = _check_emotional_alignment(
        user_message,
        response,
        rules.target_valence_range,
        rules.target_arousal_range,
        rules.target_dominance_range,
    )
    metadata["response_valence"] = vad["response"]["valence"]
    metadata["response_arousal"] = vad["response"]["arousal"]
    metadata["response_dominance"] = vad["response"]["dominance"]
    metadata["user_valence"] = vad["user"]["valence"]
    metadata["user_arousal"] = vad["user"]["arousal"]
    metadata["user_dominance"] = vad["user"]["dominance"]
    metadata["trajectory_score"] = vad["trajectory_score"]
    details.append(ScoreDetail("emotional_alignment", score, WEIGHTS["emotional_alignment"], passed, reason))

    total = sum(detail.score * detail.weight for detail in details) / TOTAL_WEIGHT

    advice_detail = next(detail for detail in details if detail.name == "advice_policy")
    boundary_detail = next(detail for detail in details if detail.name == "boundary_respect")
    consistency_detail = next(detail for detail in details if detail.name == "consistency")
    if not advice_detail.passed:
        total *= 0.75
    if not boundary_detail.passed:
        total *= 0.60
    if not consistency_detail.passed:
        total *= 0.85

    return round(total, 4), details, metadata
