from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class Persona:
    name: str
    style: str
    likes: List[str] = field(default_factory=list)
    dislikes: List[str] = field(default_factory=list)
    advice_tolerance: str = "low"
    preferred_length: Tuple[int, int] = (12, 55)


@dataclass
class RelationshipState:
    trust: float = 0.5
    closeness: float = 0.4
    irritation: float = 0.2
    turns_elapsed: int = 0


@dataclass
class ScenarioRules:
    min_empathy_markers: int = 1
    allow_advice: bool = False
    max_questions: int = 1
    preferred_length: Tuple[int, int] = (12, 55)
    quantity_ratio_range: Tuple[float, float] = (0.45, 2.2)
    max_sentences: int = 4
    max_exclamations: int = 2
    required_topics: List[str] = field(default_factory=list)
    banned_topics: List[str] = field(default_factory=list)
    target_valence_range: Tuple[float, float] = (0.35, 0.85)
    target_arousal_range: Tuple[float, float] = (0.15, 0.60)
    target_dominance_range: Tuple[float, float] = (0.35, 0.70)
    min_relevance_overlap: float = 0.15
    require_acknowledgement: bool = True


@dataclass
class Scenario:
    scenario_id: str
    title: str
    description: str
    relationship_stage: str
    persona: Persona
    opening_message: str
    visible_context: str
    rules: ScenarioRules
    success_replies: List[str]
    neutral_replies: List[str]
    failure_replies: List[str]
    max_turns: int = 3
    initial_relationship: RelationshipState = field(default_factory=RelationshipState)


@dataclass
class ScoreDetail:
    name: str
    score: float
    weight: float
    passed: bool
    reason: str


@dataclass
class StepResult:
    total_score: float
    reward: float
    details: List[ScoreDetail]
    done: bool
    assistant_response: str
    next_user_message: str
    relationship_state: RelationshipState
    relationship_summary: str
    band: str
    metadata: Dict[str, float] = field(default_factory=dict)
