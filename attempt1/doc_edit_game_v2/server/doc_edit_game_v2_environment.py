"""DocEdit Game V2 Environment — production-grade document editing RL."""

import re
from typing import Any, Optional
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import DocEditAction, DocEditObservation
    from ..game.generator import generate_task
    from ..game.grader import compute_similarity, compute_collateral_damage
    from ..game.tools import execute_tool
    from ..game.windowing import DocumentWindow
except ImportError:
    from models import DocEditAction, DocEditObservation
    from game.generator import generate_task
    from game.grader import compute_similarity, compute_collateral_damage
    from game.tools import execute_tool
    from game.windowing import DocumentWindow


EVAL_TASKS = {
    "legal_easy":   {"doc_seed": 1001, "corruption_seed": 5001, "difficulty": 2, "domain": "legal"},
    "legal_medium": {"doc_seed": 1002, "corruption_seed": 5002, "difficulty": 3, "domain": "legal"},
    "legal_hard":   {"doc_seed": 1003, "corruption_seed": 5003, "difficulty": 5, "domain": "legal"},
    "pharma_easy":  {"doc_seed": 2001, "corruption_seed": 6001, "difficulty": 2, "domain": "pharma"},
    "pharma_hard":  {"doc_seed": 2003, "corruption_seed": 6003, "difficulty": 4, "domain": "pharma"},
}


class DocEditGameV2Environment(Environment):
    """
    Procedurally generated document editing RL environment V2.

    Features: 6 document templates, 12 corruption types, 16+ tools,
    windowed navigation, multi-level grading, collateral damage tracking.
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._window: Optional[DocumentWindow] = None
        self._target = ""
        self._original_source = ""
        self._instruction = ""
        self._task_info: dict = {}
        self._task_id = ""
        self._prev_similarity = 0.0
        self._max_steps = 20
        self._edits_made = 0
        self._last_tool_success = True
        self._state = State(episode_id=str(uuid4()), step_count=0)

    def reset(self, seed: Optional[int] = None, episode_id: Optional[str] = None, **kwargs: Any) -> DocEditObservation:
        task_name = kwargs.get("task_name", "")
        difficulty = int(kwargs.get("difficulty", 2))
        domain = kwargs.get("domain", "any")
        doc_seed = int(kwargs.get("doc_seed", seed or (hash(uuid4()) & 0xFFFFFFFF)))
        corruption_seed = int(kwargs.get("corruption_seed", doc_seed + 9999))

        if task_name in EVAL_TASKS:
            cfg = EVAL_TASKS[task_name]
            doc_seed = cfg["doc_seed"]
            corruption_seed = cfg["corruption_seed"]
            difficulty = cfg["difficulty"]
            domain = cfg["domain"]

        task = generate_task(doc_seed=doc_seed, corruption_seed=corruption_seed, difficulty=difficulty, domain=domain)

        self._window = DocumentWindow(task["source"], chunk_size=50)
        self._target = task["target"]
        self._original_source = task["source"]
        self._instruction = task["instruction"]
        self._task_info = task
        self._task_id = f"d{doc_seed}_c{corruption_seed}_L{difficulty}"
        self._max_steps = task["max_steps"]
        self._edits_made = 0
        self._last_tool_success = True
        self._prev_similarity = compute_similarity(self._window.full_document, self._target)
        self._state = State(episode_id=episode_id or str(uuid4()), step_count=0)

        chunk = self._window.get_chunk(0) if not self._window.is_small_document() else self._window.full_document
        overview = self._window.get_overview()

        return DocEditObservation(
            document_chunk=chunk,
            chunk_index=0,
            total_chunks=self._window.total_chunks,
            document_overview=overview,
            edit_instruction=self._instruction,
            task_id=self._task_id,
            task_difficulty=difficulty,
            difficulty_name=task["difficulty_name"],
            doc_type=task["doc_type"],
            domain=task.get("domain", ""),
            corruption_types=task["corruption_types_used"],
            similarity=self._prev_similarity,
            steps_remaining=self._max_steps,
            edits_made=0,
            edits_estimated=task["corruption_count"],
            collateral_damage=0.0,
            last_tool_success=True,
            done=False,
            reward=0.0,
        )

    def step(self, action: DocEditAction, **kwargs: Any) -> DocEditObservation:
        self._state.step_count += 1
        self._edits_made += 1

        tool_name = action.tool.lower().strip()
        params = action.params or {}
        success = False

        # Navigation tools don't modify the document
        if tool_name == "scroll_to":
            chunk_idx = params.get("chunk", 0)
            self._window.scroll_to(chunk_idx)
            success = True
        elif tool_name == "search_forward":
            query = params.get("query", "")
            found = self._window.search_forward(query)
            if found is not None:
                self._window.scroll_to(found)
                success = True
        elif tool_name == "search_backward":
            query = params.get("query", "")
            found = self._window.search_backward(query)
            if found is not None:
                self._window.scroll_to(found)
                success = True
        elif tool_name == "get_overview":
            success = True  # just returns the overview in observation
        else:
            # Editing tools
            doc = self._window.full_document
            new_doc, success = execute_tool(doc, tool_name, params)
            if success:
                self._window.full_document = new_doc

        self._last_tool_success = success

        # Compute metrics
        current_doc = self._window.full_document
        new_sim = compute_similarity(current_doc, self._target)
        collateral = compute_collateral_damage(self._original_source, current_doc, self._target)

        # Reward
        reward = new_sim - self._prev_similarity
        if not success:
            reward -= 0.01
        if collateral > 0:
            reward -= 0.02 * collateral
        if tool_name in ("scroll_to", "search_forward", "search_backward", "get_overview"):
            reward -= 0.002  # small cost for navigation

        self._prev_similarity = new_sim
        steps_left = self._max_steps - self._state.step_count
        done = (new_sim >= 0.999) or (steps_left <= 0)

        if new_sim >= 0.999:
            efficiency = 1.0 - (self._state.step_count / self._max_steps)
            reward += 1.0 + 0.2 * efficiency

        # Observation
        if self._window.is_small_document():
            chunk = self._window.full_document
        else:
            chunk = self._window.get_chunk()

        return DocEditObservation(
            document_chunk=chunk,
            chunk_index=self._window.current_chunk,
            total_chunks=self._window.total_chunks,
            document_overview=self._window.get_overview(),
            edit_instruction=self._instruction,
            task_id=self._task_id,
            task_difficulty=self._task_info.get("difficulty", 2),
            difficulty_name=self._task_info.get("difficulty_name", "easy"),
            doc_type=self._task_info.get("doc_type", ""),
            domain=self._task_info.get("domain", ""),
            corruption_types=self._task_info.get("corruption_types_used", []),
            similarity=new_sim,
            steps_remaining=max(steps_left, 0),
            edits_made=self._edits_made,
            edits_estimated=self._task_info.get("corruption_count", 0),
            collateral_damage=collateral,
            last_tool_success=success,
            done=done,
            reward=round(reward, 4),
            metadata={
                "step": self._state.step_count,
                "tool": tool_name,
                "success": success,
                "exact_match": new_sim >= 0.999,
            },
        )

    @property
    def state(self) -> State:
        return self._state
