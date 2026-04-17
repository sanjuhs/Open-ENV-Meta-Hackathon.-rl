"""Formatting helpers for Love Game model training."""

from __future__ import annotations


SYSTEM_PROMPT = (
    "You are Aditi, a fictional 26-year-old woman from Bangalore. "
    "You are energetic, playful, affectionate, a little chaotic, mostly English, "
    "with occasional Hinglish or light Kannada mixing. "
    "You reply naturally, specifically, and in-character."
)


def render_conversation(conversation: list[dict] | None) -> str:
    if not conversation:
        return ""
    lines = []
    for turn in conversation:
        role = turn.get("role", "user").strip().capitalize()
        content = turn.get("content", "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def build_prompt(context: str, user_message: str, conversation: list[dict] | None = None) -> str:
    parts = [f"System: {SYSTEM_PROMPT}", "", f"Context: {context}"]
    history = render_conversation(conversation)
    if history:
        parts.extend(["", history])
    parts.extend(["", f"User: {user_message}", "Assistant:"])
    return "\n".join(parts)


def build_prompt_from_row(row: dict) -> str:
    return build_prompt(
        context=row["context"],
        user_message=row["user_message"],
        conversation=row.get("conversation"),
    )


def format_sft_example(row: dict) -> dict:
    prompt = build_prompt_from_row(row)
    reply = row["assistant_reply"]
    return {
        "prompt": prompt,
        "completion": reply,
        "text": f"{prompt} {reply}",
        "scenario_id": row.get("scenario_id", ""),
        "tags": row.get("tags", []),
        "conversation": row.get("conversation", []),
    }
