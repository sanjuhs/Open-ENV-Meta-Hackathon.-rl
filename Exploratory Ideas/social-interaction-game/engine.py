from __future__ import annotations

from typing import Dict, Optional

from bot import baseline_response
from models import RelationshipState, Scenario, StepResult
from scenarios import generate_procedural_scenario, get_scenarios
from verifiers import score_response


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 3)))


def relationship_summary(state: RelationshipState) -> str:
    if state.irritation >= 0.65:
        return "The connection feels tense and brittle."
    if state.trust >= 0.72 and state.closeness >= 0.60:
        return "The connection feels warm and secure."
    if state.trust >= 0.58 and state.irritation <= 0.25:
        return "The conversation feels steady and receptive."
    if state.trust < 0.40:
        return "Trust is slipping and the tone feels uncertain."
    return "The interaction is mixed and still fragile."


class SocialInteractionGame:
    def __init__(self):
        self.scenario: Optional[Scenario] = None
        self.state = RelationshipState()
        self.current_user_message = ""
        self.history = []
        self.turn_index = 0
        self.done = False

    def available_scenarios(self) -> Dict[str, Scenario]:
        return get_scenarios()

    def reset(self, scenario_id: Optional[str] = None, seed: int = 0) -> dict:
        scenarios = get_scenarios()
        self.scenario = scenarios[scenario_id] if scenario_id else generate_procedural_scenario(seed)
        self.state = RelationshipState(
            trust=self.scenario.initial_relationship.trust,
            closeness=self.scenario.initial_relationship.closeness,
            irritation=self.scenario.initial_relationship.irritation,
            turns_elapsed=0,
        )
        self.current_user_message = self.scenario.opening_message
        self.history = [{"role": "user", "text": self.current_user_message}]
        self.turn_index = 0
        self.done = False
        return self.observation()

    def observation(self) -> dict:
        if not self.scenario:
            raise RuntimeError("Game has not been reset.")
        return {
            "scenario_id": self.scenario.scenario_id,
            "title": self.scenario.title,
            "description": self.scenario.description,
            "relationship_stage": self.scenario.relationship_stage,
            "persona_name": self.scenario.persona.name,
            "persona_style": self.scenario.persona.style,
            "visible_context": self.scenario.visible_context,
            "current_user_message": self.current_user_message,
            "history": list(self.history),
            "turn_index": self.turn_index + 1,
            "max_turns": self.scenario.max_turns,
            "relationship_summary": relationship_summary(self.state),
        }

    def secret_rules(self) -> dict:
        if not self.scenario:
            raise RuntimeError("Game has not been reset.")
        rules = self.scenario.rules
        return {
            "required_topics": rules.required_topics,
            "banned_topics": rules.banned_topics,
            "preferred_length": rules.preferred_length,
            "quantity_ratio_range": rules.quantity_ratio_range,
            "allow_advice": rules.allow_advice,
            "max_questions": rules.max_questions,
            "target_valence_range": rules.target_valence_range,
            "target_arousal_range": rules.target_arousal_range,
            "target_dominance_range": rules.target_dominance_range,
        }

    def step(self, response: str) -> StepResult:
        if not self.scenario:
            raise RuntimeError("Game has not been reset.")
        if self.done:
            raise RuntimeError("Game is already finished.")

        total_score, details, metadata = score_response(self.scenario, self.current_user_message, response, self.history)
        reward = round((total_score * 2.0) - 1.0, 4)
        self.history.append({"role": "assistant", "text": response})

        if total_score >= 0.80:
            band = "success"
            self.state.trust = _clamp(self.state.trust + 0.12)
            self.state.closeness = _clamp(self.state.closeness + 0.09)
            self.state.irritation = _clamp(self.state.irritation - 0.12)
            reply_pool = self.scenario.success_replies
        elif total_score >= 0.55:
            band = "neutral"
            self.state.trust = _clamp(self.state.trust + 0.03)
            self.state.closeness = _clamp(self.state.closeness + 0.02)
            self.state.irritation = _clamp(self.state.irritation + 0.01)
            reply_pool = self.scenario.neutral_replies
        else:
            band = "failure"
            self.state.trust = _clamp(self.state.trust - 0.12)
            self.state.closeness = _clamp(self.state.closeness - 0.06)
            self.state.irritation = _clamp(self.state.irritation + 0.15)
            reply_pool = self.scenario.failure_replies

        self.state.turns_elapsed += 1
        self.turn_index += 1
        self.done = self.turn_index >= self.scenario.max_turns

        next_user_message = ""
        if not self.done:
            reply_index = min(self.turn_index - 1, len(reply_pool) - 1)
            next_user_message = reply_pool[reply_index]
            self.current_user_message = next_user_message
            self.history.append({"role": "user", "text": next_user_message})

        metadata["trust"] = self.state.trust
        metadata["closeness"] = self.state.closeness
        metadata["irritation"] = self.state.irritation

        return StepResult(
            total_score=total_score,
            reward=reward,
            details=details,
            done=self.done,
            assistant_response=response,
            next_user_message=next_user_message,
            relationship_state=self.state,
            relationship_summary=relationship_summary(self.state),
            band=band,
            metadata=metadata,
        )

    def autoplay_step(self) -> StepResult:
        if not self.scenario:
            raise RuntimeError("Game has not been reset.")
        response = baseline_response(self.scenario, self.current_user_message)
        return self.step(response)
