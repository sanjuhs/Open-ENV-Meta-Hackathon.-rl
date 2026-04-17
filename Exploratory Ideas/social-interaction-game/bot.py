from __future__ import annotations

from lexicon import estimate_vad
from models import Scenario


def baseline_response(scenario: Scenario, user_message: str) -> str:
    rules = scenario.rules
    user_vad = estimate_vad(user_message)

    empathy = "I'm really sorry." if rules.min_empathy_markers > 0 else "That is actually great."
    if user_vad["valence"] < 0.35:
        empathy = "I'm really sorry. That sounds hard."
    elif user_vad["valence"] > 0.65:
        empathy = "I love that. You sound proud."

    topic = ""
    if rules.required_topics:
        for item in rules.required_topics:
            if item in user_message.lower():
                topic = item
                break

    support = "You do not have to figure everything out right now." if not rules.allow_advice else "You handled a lot there."
    if scenario.scenario_id == "celebrate-small-win":
        support = "Shipping that fix matters, and I like that you let yourself feel the win."
    elif "mom" in scenario.scenario_id or "boundary" in scenario.scenario_id:
        support = "You do not have to rush yourself, and I am not going to push you."

    question = ""
    if rules.max_questions > 0 and scenario.scenario_id == "celebrate-small-win":
        question = " What part felt best?"

    topic_phrase = f" about the {topic}" if topic and topic not in {"today", "minute"} else ""
    return f"{empathy} I'm with you{topic_phrase}. {support}{question}".strip()
