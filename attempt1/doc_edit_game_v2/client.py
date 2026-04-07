"""DocEdit Game V2 Client."""

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

from .models import DocEditAction, DocEditObservation


class DocEditGameV2Env(EnvClient[DocEditAction, DocEditObservation, State]):
    """WebSocket client for DocEdit Game V2."""

    def _step_payload(self, action: DocEditAction) -> Dict:
        return {"tool": action.tool, "params": action.params}

    def _parse_result(self, payload: Dict) -> StepResult[DocEditObservation]:
        obs_data = payload.get("observation", {})
        observation = DocEditObservation(
            document_chunk=obs_data.get("document_chunk", ""),
            chunk_index=obs_data.get("chunk_index", 0),
            total_chunks=obs_data.get("total_chunks", 1),
            document_overview=obs_data.get("document_overview", ""),
            edit_instruction=obs_data.get("edit_instruction", ""),
            task_id=obs_data.get("task_id", ""),
            task_difficulty=obs_data.get("task_difficulty", 2),
            difficulty_name=obs_data.get("difficulty_name", "easy"),
            doc_type=obs_data.get("doc_type", ""),
            domain=obs_data.get("domain", ""),
            corruption_types=obs_data.get("corruption_types", []),
            similarity=obs_data.get("similarity", 0.0),
            steps_remaining=obs_data.get("steps_remaining", 0),
            edits_made=obs_data.get("edits_made", 0),
            edits_estimated=obs_data.get("edits_estimated", 0),
            collateral_damage=obs_data.get("collateral_damage", 0.0),
            last_tool_success=obs_data.get("last_tool_success", True),
            done=payload.get("done", False),
            reward=payload.get("reward"),
            metadata=obs_data.get("metadata", {}),
        )
        return StepResult(observation=observation, reward=payload.get("reward"), done=payload.get("done", False))

    def _parse_state(self, payload: Dict) -> State:
        return State(episode_id=payload.get("episode_id"), step_count=payload.get("step_count", 0))
