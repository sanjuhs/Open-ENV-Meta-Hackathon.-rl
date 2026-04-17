"""Shared prompt, dataset, and reward helpers for DocEdit training."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DOCEDIT_DIR = ROOT / "attempt1" / "doc_edit_game_v2"
if str(DOCEDIT_DIR) not in sys.path:
    sys.path.insert(0, str(DOCEDIT_DIR))

from game.generator import generate_task  # noqa: E402
from game.grader import grade_task  # noqa: E402


SYSTEM_PROMPT = (
    "You are an expert Word-style document repair model. "
    "Repair the corrupted document while preserving the original structure and valid markup. "
    "Return only the corrected document markup. Do not add explanations, bullet points, or code fences."
)


def task_from_case(case: Any) -> dict[str, Any]:
    return generate_task(
        doc_seed=case.doc_seed,
        corruption_seed=case.corruption_seed,
        difficulty=case.difficulty,
        domain=case.domain,
    )


def build_direct_rewrite_prompt(task: dict[str, Any]) -> str:
    return (
        f"{SYSTEM_PROMPT}\n\n"
        "Scenario:\n"
        f"- Domain: {task['domain']}\n"
        f"- Document type: {task['doc_type']}\n"
        f"- Difficulty: {task['difficulty']} ({task['difficulty_name']})\n"
        f"- Corruption count: {task['corruption_count']}\n\n"
        "Instruction:\n"
        f"{task['instruction']}\n\n"
        "Corrupted document:\n"
        f"{task['source']}\n\n"
        "Output contract:\n"
        "- Return the repaired document only.\n"
        "- Preserve the document markup shape.\n"
        "- Do not wrap the answer in markdown fences.\n"
    )


def build_direct_rewrite_messages(task: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Repair this corrupted structured document and return only the corrected markup.\n\n"
                f"Instruction:\n{task['instruction']}\n\n"
                f"Corrupted document:\n{task['source']}"
            ),
        },
    ]


def build_sft_record(*, case_id: str, task: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "prompt": build_direct_rewrite_prompt(task),
        "completion": task["target"],
        "doc_seed": task["doc_seed"],
        "corruption_seed": task["corruption_seed"],
        "difficulty": task["difficulty"],
        "domain": task["domain"],
        "doc_type": task["doc_type"],
        "instruction": task["instruction"],
    }


def build_grpo_record(*, case_id: str, task: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "prompt": build_direct_rewrite_prompt(task),
        "source": task["source"],
        "target": task["target"],
        "instruction": task["instruction"],
        "doc_seed": task["doc_seed"],
        "corruption_seed": task["corruption_seed"],
        "difficulty": task["difficulty"],
        "domain": task["domain"],
        "doc_type": task["doc_type"],
        "corruptions_json": json.dumps(task["corruptions"]),
    }


def extract_document_from_completion(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return ""

    fenced = re.findall(r"```(?:\w+)?\n(.*?)```", cleaned, flags=re.DOTALL)
    if fenced:
        cleaned = fenced[-1].strip()

    tagged = re.search(r"<document>(.*)</document>", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if tagged:
        cleaned = tagged.group(1).strip()

    if "FINAL_DOCUMENT:" in cleaned:
        cleaned = cleaned.split("FINAL_DOCUMENT:", 1)[1].strip()

    lines = cleaned.splitlines()
    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith(("<think>", "</think>", "assistant:", "here is")):
            continue
        filtered_lines.append(line)
    return "\n".join(filtered_lines).strip()


def parse_corruptions(value: str | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return value
    if not value:
        return []
    return json.loads(value)


def score_document(
    *,
    source: str,
    target: str,
    corruptions: str | list[dict[str, Any]],
    edited_document: str,
) -> dict[str, float]:
    return grade_task(
        current=edited_document,
        target=target,
        original=source,
        corruptions=parse_corruptions(corruptions),
    )
