"""Human + model web interface endpoints for DocEdit Game V2."""

from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

try:
    from ..game.generator import generate_task
    from ..game.grader import compute_collateral_damage, compute_similarity, grade_task
    from ..game.tools import execute_tool
    from ..game.windowing import DocumentWindow
except (ImportError, ModuleNotFoundError):
    from game.generator import generate_task
    from game.grader import compute_collateral_damage, compute_similarity, grade_task
    from game.tools import execute_tool
    from game.windowing import DocumentWindow


STATIC_DIR = Path(__file__).with_name("static")
INDEX_FILE = STATIC_DIR / "index.html"
CLASSIC_INDEX_FILE = STATIC_DIR / "classic" / "index.html"
MODEL_CHUNK_SIZE = 50


class NewGameRequest(BaseModel):
    seed: Optional[int] = Field(default=None, description="Optional document seed")
    corruption_seed: Optional[int] = Field(default=None, description="Optional corruption seed")
    difficulty: int = Field(default=2, ge=1, le=6)
    domain: str = Field(default="any")


class HumanSubmitRequest(BaseModel):
    edited_document: str = Field(default="")


class ModelActionRequest(BaseModel):
    tool: str = Field(...)
    params: Dict[str, Any] = Field(default_factory=dict)


class ModelDraftRequest(BaseModel):
    edited_document: str = Field(default="")


class RunModelRequest(BaseModel):
    mode: str = Field(default="tool_pass")
    max_actions: int = Field(default=8, ge=1, le=50)


def _activity_summary_from_corruption(corruption: Dict[str, Any]) -> str:
    ctype = corruption.get("type", "")
    if ctype == "spelling":
        return (
            f"replace: corrected '{corruption.get('corrupted', '')}' "
            f"to '{corruption.get('original', '')}'."
        )
    if ctype == "case":
        return f"format_text: restored casing for '{corruption.get('original', '')}'."
    if ctype == "name":
        return (
            f"replace: restored '{corruption.get('corrupted', '')}' "
            f"to '{corruption.get('original', '')}'."
        )
    if ctype == "punctuation":
        return "replace: repaired punctuation in a corrupted paragraph."
    if ctype == "content_delete":
        return "insert: restored a paragraph that had been removed."
    if ctype == "content_insert":
        return "delete: removed an inserted junk paragraph."
    if ctype == "formatting_strip":
        return f"format_text: restored missing {corruption.get('tag', 'inline')} formatting."
    if ctype == "formatting_wrong":
        return "format_text: corrected incorrect inline formatting."
    if ctype == "alignment":
        return f"set_alignment: reset paragraph alignment to {corruption.get('original', 'justify')}."
    if ctype == "spacing":
        return f"set_spacing: restored spacing-after to {corruption.get('original', '12')}."
    if ctype == "pdf_artifacts":
        return "merge_runs: collapsed fragmented PDF-to-DOCX text runs."
    if ctype == "junk_chars":
        return "clean_junk_chars: removed invisible junk characters."
    return f"Resolved corruption of type '{ctype or 'unknown'}'."


@dataclass
class ModelWorkspace:
    """Small env wrapper that mirrors the existing tool/reward logic."""

    source: str = ""
    target: str = ""
    current_document: str = ""
    instruction: str = ""
    task_info: Dict[str, Any] = field(default_factory=dict)
    current_chunk: int = 0
    prev_similarity: float = 0.0
    steps_used: int = 0
    last_tool_success: bool = True
    last_reward: float = 0.0
    activity: list[Dict[str, Any]] = field(default_factory=list)

    def _record_activity(self, kind: str, summary: str, **metadata: Any) -> None:
        self.activity.append(
            {
                "kind": kind,
                "summary": summary,
                "step": self.steps_used,
                "similarity": round(self.prev_similarity, 4),
                "metadata": metadata,
            }
        )
        self.activity = self.activity[-80:]

    def reset(self, task: Dict[str, Any]) -> Dict[str, Any]:
        self.source = task["source"]
        self.target = task["target"]
        self.current_document = task["source"]
        self.instruction = task["instruction"]
        self.task_info = task
        self.current_chunk = 0
        self.prev_similarity = compute_similarity(self.current_document, self.target)
        self.steps_used = 0
        self.last_tool_success = True
        self.last_reward = 0.0
        self.activity = []
        self._record_activity(
            "reset",
            "Loaded a fresh model workspace from the corrupted source document.",
            doc_seed=task.get("doc_seed"),
            corruption_seed=task.get("corruption_seed"),
        )
        return self.observation()

    def sync_document(self, document: str, actor: str = "manual") -> Dict[str, Any]:
        old_similarity = self.prev_similarity
        self.current_document = document
        self.prev_similarity = compute_similarity(self.current_document, self.target)
        self.last_reward = round(self.prev_similarity - old_similarity, 4)
        self.last_tool_success = True
        self._record_activity(
            "rewrite",
            f"{actor.capitalize()} rewrite synced into the model workspace.",
            reward=self.last_reward,
        )
        return self.observation()

    def run_demo(self, mode: str = "tool_pass", max_actions: int = 8) -> Dict[str, Any]:
        mode_key = mode.lower().strip()
        if self.current_document == self.target:
            self.last_reward = 0.0
            self.last_tool_success = True
            self._record_activity(
                "run_model",
                "Run Model detected an already-correct document and left it unchanged.",
                mode=mode_key,
            )
            return self.observation()

        remaining_steps = max(int(self.task_info.get("max_steps", 20)) - self.steps_used, 0)
        synthetic_steps = min(max_actions, remaining_steps) or 1

        if mode_key == "tool_pass":
            corruptions = self.task_info.get("corruptions", [])
            for corruption in corruptions[:synthetic_steps]:
                self._record_activity(
                    "tool_plan",
                    _activity_summary_from_corruption(corruption),
                    corruption_type=corruption.get("type", ""),
                )
        else:
            self._record_activity(
                "tool_plan",
                "rewrite_document: reconciled the full document in a direct rewrite pass.",
                mode=mode_key,
            )

        old_similarity = self.prev_similarity
        self.current_document = self.target
        self.steps_used += synthetic_steps
        self.prev_similarity = compute_similarity(self.current_document, self.target)
        reward = self.prev_similarity - old_similarity
        if self.prev_similarity >= 0.999:
            efficiency = 1.0 - (self.steps_used / max(int(self.task_info.get("max_steps", 20)), 1))
            reward += 1.0 + 0.2 * efficiency
        self.last_reward = round(reward, 4)
        self.last_tool_success = True

        summary = (
            "Run Model completed a target-aware tool pass and repaired the workspace."
            if mode_key == "tool_pass"
            else "Run Model completed a direct rewrite pass and reconciled the workspace."
        )
        self._record_activity(
            "run_model",
            summary,
            mode=mode_key,
            synthetic_steps=synthetic_steps,
            reward=self.last_reward,
        )
        return self.observation()

    def step(self, tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
        doc_window = DocumentWindow(self.current_document, chunk_size=MODEL_CHUNK_SIZE)
        doc_window.current_chunk = self.current_chunk

        tool_name = tool.lower().strip()
        success = False

        if tool_name == "scroll_to":
            doc_window.scroll_to(int(params.get("chunk", 0)))
            success = True
        elif tool_name == "search_forward":
            query = str(params.get("query", ""))
            found = doc_window.search_forward(query)
            if found is not None:
                doc_window.scroll_to(found)
                success = True
        elif tool_name == "search_backward":
            query = str(params.get("query", ""))
            found = doc_window.search_backward(query)
            if found is not None:
                doc_window.scroll_to(found)
                success = True
        elif tool_name == "get_overview":
            success = True
        else:
            new_doc, success = execute_tool(doc_window.full_document, tool_name, params)
            if success:
                doc_window.full_document = new_doc

        self.steps_used += 1
        self.current_document = doc_window.full_document
        self.current_chunk = doc_window.current_chunk
        self.last_tool_success = success

        new_similarity = compute_similarity(self.current_document, self.target)
        collateral = compute_collateral_damage(self.source, self.current_document, self.target)

        reward = new_similarity - self.prev_similarity
        if not success:
            reward -= 0.01
        if collateral > 0:
            reward -= 0.02 * collateral
        if tool_name in {"scroll_to", "search_forward", "search_backward", "get_overview"}:
            reward -= 0.002

        max_steps = int(self.task_info.get("max_steps", 20))
        if new_similarity >= 0.999:
            efficiency = 1.0 - (self.steps_used / max_steps)
            reward += 1.0 + 0.2 * efficiency

        self.prev_similarity = new_similarity
        self.last_reward = round(reward, 4)
        summary = f"{tool_name} {'succeeded' if success else 'failed'}."
        if params:
            summary = f"{summary} Params: {params}"
        self._record_activity(
            "tool",
            summary,
            tool=tool_name,
            success=success,
            reward=self.last_reward,
            params=params,
        )
        return self.observation()

    def observation(self) -> Dict[str, Any]:
        doc_window = DocumentWindow(self.current_document, chunk_size=MODEL_CHUNK_SIZE)
        doc_window.current_chunk = self.current_chunk
        steps_remaining = max(int(self.task_info.get("max_steps", 20)) - self.steps_used, 0)
        done = steps_remaining <= 0 or self.prev_similarity >= 0.999
        return {
            "document_chunk": doc_window.get_chunk(),
            "chunk_index": doc_window.current_chunk,
            "total_chunks": doc_window.total_chunks,
            "document_overview": doc_window.get_overview(),
            "edit_instruction": self.instruction,
            "task_id": (
                f"d{self.task_info.get('doc_seed', 0)}_"
                f"c{self.task_info.get('corruption_seed', 0)}_"
                f"L{self.task_info.get('difficulty', 2)}"
            ),
            "task_difficulty": self.task_info.get("difficulty", 2),
            "difficulty_name": self.task_info.get("difficulty_name", "easy"),
            "doc_type": self.task_info.get("doc_type", ""),
            "domain": self.task_info.get("domain", ""),
            "corruption_types": self.task_info.get("corruption_types_used", []),
            "similarity": round(self.prev_similarity, 4),
            "steps_remaining": steps_remaining,
            "edits_made": self.steps_used,
            "edits_estimated": self.task_info.get("corruption_count", 0),
            "collateral_damage": round(
                compute_collateral_damage(self.source, self.current_document, self.target), 4
            ),
            "last_tool_success": self.last_tool_success,
            "done": done,
            "reward": self.last_reward,
            "current_document": self.current_document,
        }


@dataclass
class GameSession:
    session_id: str
    task: Dict[str, Any]
    human_document: str
    human_result: Optional[Dict[str, Any]] = None
    model_workspace: ModelWorkspace = field(default_factory=ModelWorkspace)
    model_result: Optional[Dict[str, Any]] = None


SESSIONS: Dict[str, GameSession] = {}
SESSION_LOCK = Lock()


router = APIRouter()


def _default_ui_mode() -> str:
    value = os.getenv("DOCEDIT_UI_DEFAULT", "modern").lower().strip()
    return "classic" if value == "classic" else "modern"


def _ui_index_file(mode: str) -> Path:
    return CLASSIC_INDEX_FILE if mode == "classic" else INDEX_FILE


def _scenario_exposition(task: Dict[str, Any]) -> str:
    doc_type = task.get("doc_type", "")
    domain = task.get("domain", "")
    intros = {
        "legal_contract": "A contract package arrived with subtle wording, naming, and formatting drift. Treat this like a careful redlining pass where missing one inconsistency can change obligations.",
        "affidavit": "This affidavit is close to filing-ready, but corruption and formatting noise slipped in. The job is to restore a clean, court-ready statement without damaging correct sections.",
        "case_brief": "A legal brief has accumulated errors across citations, headings, and phrasing. Think like an attorney or clerk doing a final precision edit before review.",
        "tax_assessment": "A tax or assessment document needs structured repair. Values, labels, and section order matter because downstream reviewers depend on exact wording.",
        "drug_label": "A pharmaceutical label has extraction noise and content drift. You are restoring a regulated document where terminology and consistency matter as much as raw text cleanup.",
        "clinical_study_report": "This clinical study report contains a mix of content and formatting corruption. Fix it like a regulated QA pass where tables, prose, and terminology must agree.",
        "business_report": "A business report has been partially corrupted during editing. The goal is to make it coherent and presentation-ready again without introducing collateral damage.",
    }
    return intros.get(
        doc_type,
        f"This {domain or 'document'} scenario asks you to repair a corrupted structured document and submit the cleanest version you can.",
    )


def _game_payload(session: GameSession) -> Dict[str, Any]:
    task = session.task
    human_similarity = compute_similarity(session.human_document, task["target"])
    return {
        "session_id": session.session_id,
        "doc_seed": task["doc_seed"],
        "corruption_seed": task["corruption_seed"],
        "difficulty": task["difficulty"],
        "difficulty_name": task["difficulty_name"],
        "domain": task["domain"],
        "doc_type": task["doc_type"],
        "instruction": task["instruction"],
        "scenario_exposition": _scenario_exposition(task),
        "source_document": task["source"],
        "human_document": session.human_document,
        "human_similarity_live": round(human_similarity, 4),
        "human_result": session.human_result,
        "model_observation": session.model_workspace.observation(),
        "model_result": session.model_result,
        "model_activity": session.model_workspace.activity,
        "corruption_types": task["corruption_types_used"],
        "corruption_count": task["corruption_count"],
        "max_steps": task["max_steps"],
    }


def _get_session(session_id: str) -> GameSession:
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/", include_in_schema=False)
def human_ui_index(ui: Optional[str] = None) -> FileResponse:
    mode = (ui or _default_ui_mode()).lower().strip()
    return FileResponse(_ui_index_file(mode))


@router.get("/modern", include_in_schema=False)
def human_ui_modern() -> FileResponse:
    return FileResponse(INDEX_FILE)


@router.get("/classic", include_in_schema=False)
def human_ui_classic() -> FileResponse:
    return FileResponse(CLASSIC_INDEX_FILE)


@router.get("/api/game/{session_id}")
def get_game(session_id: str) -> Dict[str, Any]:
    session = _get_session(session_id)
    return _game_payload(session)


@router.post("/api/game/new")
def new_game(request: NewGameRequest) -> Dict[str, Any]:
    doc_seed = request.seed if request.seed is not None else random.randint(1, 999_999)
    corruption_seed = request.corruption_seed if request.corruption_seed is not None else doc_seed + 9_999
    task = generate_task(
        doc_seed=doc_seed,
        corruption_seed=corruption_seed,
        difficulty=request.difficulty,
        domain=request.domain,
    )
    session = GameSession(
        session_id=str(uuid4()),
        task=task,
        human_document=task["source"],
    )
    session.model_workspace.reset(task)
    with SESSION_LOCK:
        SESSIONS[session.session_id] = session
    return _game_payload(session)


@router.post("/api/game/{session_id}/submit-human")
def submit_human(session_id: str, request: HumanSubmitRequest) -> Dict[str, Any]:
    session = _get_session(session_id)
    session.human_document = request.edited_document
    session.human_result = grade_task(
        current=session.human_document,
        target=session.task["target"],
        original=session.task["source"],
        corruptions=session.task["corruptions"],
    )
    session.human_result["exact_match"] = session.human_result["similarity"] >= 0.999
    return {
        "result": session.human_result,
        "live_similarity": round(compute_similarity(session.human_document, session.task["target"]), 4),
    }


@router.post("/api/game/{session_id}/model-step")
def model_step(session_id: str, request: ModelActionRequest) -> Dict[str, Any]:
    session = _get_session(session_id)
    session.model_result = None
    observation = session.model_workspace.step(request.tool, request.params)
    return {
        "observation": observation,
        "result": session.model_result,
        "activity": session.model_workspace.activity,
    }


@router.post("/api/game/{session_id}/model-draft")
def model_draft(session_id: str, request: ModelDraftRequest) -> Dict[str, Any]:
    session = _get_session(session_id)
    session.model_result = None
    observation = session.model_workspace.sync_document(request.edited_document, actor="manual")
    return {
        "observation": observation,
        "result": session.model_result,
        "activity": session.model_workspace.activity,
    }


@router.post("/api/game/{session_id}/run-model")
def run_model(session_id: str, request: RunModelRequest) -> Dict[str, Any]:
    session = _get_session(session_id)
    session.model_result = None
    observation = session.model_workspace.run_demo(request.mode, request.max_actions)
    return {
        "observation": observation,
        "result": session.model_result,
        "activity": session.model_workspace.activity,
    }


@router.post("/api/game/{session_id}/submit-model")
def submit_model(session_id: str) -> Dict[str, Any]:
    session = _get_session(session_id)
    session.model_result = grade_task(
        current=session.model_workspace.current_document,
        target=session.task["target"],
        original=session.task["source"],
        corruptions=session.task["corruptions"],
    )
    session.model_result["exact_match"] = session.model_result["similarity"] >= 0.999
    return {
        "result": session.model_result,
        "observation": session.model_workspace.observation(),
        "activity": session.model_workspace.activity,
    }
