"""Pydantic models for DocEdit Game V2."""

from typing import Dict, List, Optional
from openenv.core.env_server.types import Action, Observation
from pydantic import Field


class DocEditAction(Action):
    """Agent submits a tool call per step."""

    tool: str = Field(
        ...,
        description="Tool name: replace, insert, delete, format_text, highlight, "
        "set_alignment, set_spacing, clean_junk_chars, merge_runs, "
        "move, add_redline, accept_change, reject_change, add_comment, "
        "scroll_to, search_forward",
    )
    params: Dict = Field(
        default_factory=dict,
        description="Tool-specific parameters (target, content, position, format, color, line_index, etc.)",
    )


class DocEditObservation(Observation):
    """Rich observation with document chunk + context."""

    # Current view
    document_chunk: str = Field(default="", description="Currently visible document chunk (XML)")
    chunk_index: int = Field(default=0, description="Current chunk position")
    total_chunks: int = Field(default=1, description="Total chunks in document")

    # Context
    document_overview: str = Field(default="", description="High-level doc structure (headings + positions)")

    # Task info
    edit_instruction: str = Field(default="", description="Natural language description of edits needed")
    task_id: str = Field(default="", description="Unique task identifier")
    task_difficulty: int = Field(default=2, description="Difficulty level (1-6)")
    difficulty_name: str = Field(default="easy", description="Difficulty name")
    doc_type: str = Field(default="", description="Document template type")
    domain: str = Field(default="", description="Domain: legal, pharma, business")
    corruption_types: List[str] = Field(default_factory=list, description="Corruption types applied")

    # Progress
    similarity: float = Field(default=0.0, description="Overall doc similarity to target (0.0-1.0)")
    steps_remaining: int = Field(default=0, description="Steps left in episode")
    edits_made: int = Field(default=0, description="Tool calls so far")
    edits_estimated: int = Field(default=0, description="Estimated corruptions to fix")
    collateral_damage: float = Field(default=0.0, description="Fraction of correct text accidentally damaged")

    # Last action feedback
    last_tool_success: bool = Field(default=True, description="Whether the last tool call succeeded")
