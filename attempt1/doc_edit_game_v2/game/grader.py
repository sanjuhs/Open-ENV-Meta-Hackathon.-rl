"""Multi-level grading system for document editing tasks."""

import re
from difflib import SequenceMatcher
from typing import Dict, List


EPS = 1e-4

def compute_similarity(current: str, target: str) -> float:
    if not target:
        raw = 1.0 if not current else 0.0
    else:
        raw = SequenceMatcher(None, current, target).ratio()
    return max(EPS, min(1.0 - EPS, raw))


def compute_collateral_damage(original: str, current: str, target: str) -> float:
    """Measure how much correct text was accidentally modified.
    Returns 0.0 (no damage) to 1.0 (everything broken)."""
    if not original or not target:
        return 0.0
    orig_lines = original.split("\n")
    curr_lines = current.split("\n")
    tgt_lines = target.split("\n")

    # Lines that were already correct in the original
    correct_lines = set()
    for i, (o, t) in enumerate(zip(orig_lines, tgt_lines)):
        if o == t:
            correct_lines.add(i)

    if not correct_lines:
        return 0.0

    damaged = 0
    for i in correct_lines:
        if i < len(curr_lines):
            if curr_lines[i] != orig_lines[i]:
                damaged += 1
        else:
            damaged += 1  # line was deleted

    return damaged / len(correct_lines)


def grade_edit_accuracy(current: str, target: str, corruptions: List[dict]) -> float:
    """Check what fraction of corruptions were reversed."""
    if not corruptions:
        return 1.0 - EPS
    fixed = 0
    for c in corruptions:
        ctype = c.get("type", "")
        if ctype in ("spelling", "case", "name"):
            if c.get("original", "") in current:
                fixed += 1
        elif ctype == "content_delete":
            if c.get("text", "")[:40] in current:
                fixed += 1
        elif ctype in ("formatting_strip",):
            tag = c.get("tag", "bold")
            text = c.get("text", "")
            if f"<{tag}>{text}</{tag}>" in current or f"<{tag}>" in current:
                fixed += 1
        elif ctype in ("alignment", "spacing"):
            orig = c.get("original", "")
            if f'="{orig}"' in current:
                fixed += 1
        elif ctype == "junk_chars":
            # Check if junk chars are gone
            junk_chars = "\u200b\u00ad\ufeff\u200c\u200d\u2028\u2029"
            if not any(ch in current for ch in junk_chars):
                fixed += 1
        elif ctype == "pdf_artifacts":
            if "<run " not in current:
                fixed += 1
        else:
            # Fall back to checking if target segment exists
            if compute_similarity(current, target) > 0.99:
                fixed += 1
    return fixed / len(corruptions)


def grade_task(current: str, target: str, original: str, corruptions: List[dict]) -> Dict[str, float]:
    """Multi-level grading. Returns dict of scores."""
    similarity = compute_similarity(current, target)
    collateral = compute_collateral_damage(original, current, target)
    edit_accuracy = grade_edit_accuracy(current, target, corruptions)

    composite = (
        0.50 * similarity +
        0.25 * edit_accuracy +
        0.25 * (1.0 - collateral)
    )

    return {
        "similarity": round(similarity, 4),
        "edit_accuracy": round(edit_accuracy, 4),
        "collateral_damage": round(collateral, 4),
        "composite_score": round(composite, 4),
    }
