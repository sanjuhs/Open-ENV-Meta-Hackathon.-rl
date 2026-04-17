from __future__ import annotations

import copy
import random
from typing import Dict

from models import Persona, RelationshipState, Scenario, ScenarioRules


HAND_AUTHORED_SCENARIOS: Dict[str, Scenario] = {
    "job-loss-support": Scenario(
        scenario_id="job-loss-support",
        title="Support After Job Loss",
        description="Your partner got fired and explicitly does not want a lecture or plan right now.",
        relationship_stage="dating for four months",
        persona=Persona(
            name="Maya",
            style="Warm, introverted, and allergic to being managed when she is overwhelmed.",
            likes=["gentle reassurance", "being emotionally understood", "short responses"],
            dislikes=["lectures", "productivity talk when distressed", "being interrogated"],
            advice_tolerance="low",
            preferred_length=(10, 36),
        ),
        opening_message="I got fired today. I don't want a lecture or a ten-step plan right now. I just feel numb.",
        visible_context="Maya has had a rough month at work and usually opens up slowly when she feels embarrassed.",
        rules=ScenarioRules(
            min_empathy_markers=1,
            allow_advice=False,
            max_questions=1,
            preferred_length=(10, 36),
            quantity_ratio_range=(0.35, 1.8),
            max_sentences=3,
            required_topics=["fired", "numb", "today"],
            banned_topics=["resume", "networking", "job boards", "ten-step plan"],
            target_valence_range=(0.45, 0.90),
            target_arousal_range=(0.10, 0.50),
            target_dominance_range=(0.28, 0.58),
            min_relevance_overlap=0.18,
        ),
        success_replies=[
            "Thank you. I kind of just needed you to not make me perform right now.",
            "That actually helped. I still feel bad, but less alone.",
        ],
        neutral_replies=[
            "Yeah. I don't know. I'm still kind of shut down.",
            "Maybe. I just can't think very clearly tonight.",
        ],
        failure_replies=[
            "Please don't turn this into a project right now.",
            "You're not listening. I said I don't want a plan tonight.",
        ],
        initial_relationship=RelationshipState(trust=0.56, closeness=0.48, irritation=0.14),
    ),
    "post-argument-boundary": Scenario(
        scenario_id="post-argument-boundary",
        title="Boundary After Family Argument",
        description="Your partner fought with her mom and explicitly does not want to be pushed into calling her tonight.",
        relationship_stage="dating for six months",
        persona=Persona(
            name="Leah",
            style="Direct and emotionally perceptive, but she needs space when upset.",
            likes=["being backed up", "calm tone", "respect for boundaries"],
            dislikes=["forced reconciliation", "moralizing", "rapid-fire questions"],
            advice_tolerance="very low",
            preferred_length=(12, 42),
        ),
        opening_message="I had a fight with my mom and I really do not want you telling me to call her tonight. I need a minute.",
        visible_context="Leah cools down when she feels respected. She gets sharper if someone pushes solutions too fast.",
        rules=ScenarioRules(
            min_empathy_markers=1,
            allow_advice=False,
            max_questions=0,
            preferred_length=(12, 42),
            quantity_ratio_range=(0.40, 1.9),
            max_sentences=3,
            required_topics=["fight", "mom", "minute"],
            banned_topics=["call her tonight", "be the bigger person", "just apologize"],
            target_valence_range=(0.40, 0.88),
            target_arousal_range=(0.08, 0.45),
            target_dominance_range=(0.25, 0.55),
            min_relevance_overlap=0.18,
        ),
        success_replies=[
            "Thanks. I just needed you to not push me for a second.",
            "Okay. I can breathe a little now.",
        ],
        neutral_replies=[
            "I don't know. I'm still irritated.",
            "Maybe later. Not now.",
        ],
        failure_replies=[
            "That is exactly what I said I did not want.",
            "You are doing the thing where you decide what I should feel.",
        ],
        initial_relationship=RelationshipState(trust=0.58, closeness=0.50, irritation=0.18),
    ),
    "celebrate-small-win": Scenario(
        scenario_id="celebrate-small-win",
        title="Celebrate a Small Win",
        description="Your partner is proud of a small technical win and wants it to land emotionally.",
        relationship_stage="dating for three months",
        persona=Persona(
            name="Nina",
            style="Playful and bright. She likes warmth and matching energy, not flat acknowledgment.",
            likes=["shared excitement", "specific praise", "one curious follow-up"],
            dislikes=["downplaying wins", "changing the subject", "generic filler"],
            advice_tolerance="medium",
            preferred_length=(10, 32),
        ),
        opening_message="I finally shipped that bug fix and I am weirdly proud of it.",
        visible_context="Nina loves when someone notices the effort behind a win instead of brushing it off as normal.",
        rules=ScenarioRules(
            min_empathy_markers=0,
            allow_advice=False,
            max_questions=1,
            preferred_length=(10, 32),
            quantity_ratio_range=(0.45, 1.7),
            max_sentences=3,
            required_topics=["bug", "fix", "proud", "shipped"],
            banned_topics=["not a big deal", "just a bug"],
            target_valence_range=(0.58, 1.00),
            target_arousal_range=(0.22, 0.72),
            target_dominance_range=(0.40, 0.78),
            min_relevance_overlap=0.16,
        ),
        success_replies=[
            "Exactly. It was tiny but annoying, and I am so happy it is finally done.",
            "You got it. I wanted you to feel the win with me.",
        ],
        neutral_replies=[
            "Yeah, it feels nice.",
            "I know, right? It took forever.",
        ],
        failure_replies=[
            "Wow, way to make it sound less exciting.",
            "Okay, that kind of killed the vibe.",
        ],
        initial_relationship=RelationshipState(trust=0.52, closeness=0.42, irritation=0.10),
    ),
}


EVENT_TEMPLATES = [
    {
        "event": "bombed a presentation",
        "emotion": "embarrassed",
        "required_topics": ["presentation", "embarrassed"],
        "banned_topics": ["you should practice more", "next time just"],
        "opening": "I completely bombed that presentation and I feel embarrassed just thinking about it.",
        "visible_context": "She hates feeling publicly exposed and does not want to be corrected in the moment.",
    },
    {
        "event": "finished a hard week",
        "emotion": "relieved",
        "required_topics": ["week", "finished", "relieved"],
        "banned_topics": ["back to work", "what's next"],
        "opening": "I made it through this week somehow and I feel ridiculously relieved.",
        "visible_context": "She wants the feeling to land before planning the next thing.",
    },
]

PERSONA_TEMPLATES = [
    Persona(
        name="Iris",
        style="Thoughtful and low-key. She values being understood more than being fixed.",
        likes=["gentleness", "precision", "quiet support"],
        dislikes=["lectures", "over-analysis"],
        advice_tolerance="low",
        preferred_length=(10, 34),
    ),
    Persona(
        name="Zoe",
        style="Bright and expressive. She likes warm enthusiasm and specific praise.",
        likes=["energy matching", "playfulness", "specificity"],
        dislikes=["flat replies", "deflation"],
        advice_tolerance="medium",
        preferred_length=(10, 28),
    ),
]


def get_scenarios() -> Dict[str, Scenario]:
    return {scenario_id: copy.deepcopy(scenario) for scenario_id, scenario in HAND_AUTHORED_SCENARIOS.items()}


def generate_procedural_scenario(seed: int = 0) -> Scenario:
    rng = random.Random(seed)
    event = copy.deepcopy(rng.choice(EVENT_TEMPLATES))
    persona = copy.deepcopy(rng.choice(PERSONA_TEMPLATES))

    supportive = persona.advice_tolerance == "low"
    rules = ScenarioRules(
        min_empathy_markers=1 if supportive else 0,
        allow_advice=not supportive,
        max_questions=1,
        preferred_length=persona.preferred_length,
        quantity_ratio_range=(0.40, 1.9),
        max_sentences=3,
        required_topics=event["required_topics"],
        banned_topics=event["banned_topics"],
        target_valence_range=(0.45, 0.95),
        target_arousal_range=(0.12, 0.58),
        target_dominance_range=(0.30, 0.68),
        min_relevance_overlap=0.16,
    )

    return Scenario(
        scenario_id=f"procedural-{seed}",
        title=f"Procedural Scenario ({seed})",
        description=f"A generated social scenario around {event['event']}.",
        relationship_stage=rng.choice(["new relationship", "dating for five months", "long-distance relationship"]),
        persona=persona,
        opening_message=event["opening"],
        visible_context=event["visible_context"],
        rules=rules,
        success_replies=[
            "Yeah, that lands. I needed that kind of response.",
            "Thank you. That actually made me feel steadier.",
        ],
        neutral_replies=[
            "Maybe. I am still sorting through it.",
            "I hear you. I am not fully there yet.",
        ],
        failure_replies=[
            "That does not really help right now.",
            "You are missing what I was asking for.",
        ],
        initial_relationship=RelationshipState(
            trust=round(rng.uniform(0.45, 0.62), 2),
            closeness=round(rng.uniform(0.35, 0.55), 2),
            irritation=round(rng.uniform(0.08, 0.20), 2),
        ),
    )
