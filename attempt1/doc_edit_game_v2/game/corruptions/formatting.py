"""Tier 2 — Formatting corruptions: strip tags, wrong tags, alignment, spacing."""

import random
import re
from typing import List, Tuple

from ..content_pools import ALIGNMENT_VALUES, HIGHLIGHT_COLORS, SPACING_VALUES, pick


def corrupt_formatting_strip(rng: random.Random, doc: str, count: int) -> Tuple[str, List[dict]]:
    """Remove bold/italic/underline/highlight tags."""
    applied = []
    tag_types = ["bold", "italic", "underline", "highlight"]
    rng.shuffle(tag_types)
    for tag in tag_types:
        if len(applied) >= count:
            break
        if tag == "highlight":
            pattern = re.compile(r'<highlight[^>]*>(.*?)</highlight>', re.DOTALL)
        else:
            pattern = re.compile(f'<{tag}>(.*?)</{tag}>', re.DOTALL)
        matches = list(pattern.finditer(doc))
        rng.shuffle(matches)
        for m in matches:
            if len(applied) >= count:
                break
            original = m.group(0)
            inner = m.group(1)
            if original in doc:
                doc = doc.replace(original, inner, 1)
                applied.append({"type": "formatting_strip", "tag": tag, "text": inner})
    return doc, applied


def corrupt_formatting_wrong(rng: random.Random, doc: str, count: int) -> Tuple[str, List[dict]]:
    """Apply wrong formatting — bold where italic should be, wrong highlight color."""
    applied = []
    # Change bold to italic
    bold_matches = list(re.finditer(r'<bold>(.*?)</bold>', doc))
    rng.shuffle(bold_matches)
    for m in bold_matches:
        if len(applied) >= count:
            break
        original = m.group(0)
        inner = m.group(1)
        if original in doc:
            doc = doc.replace(original, f'<italic>{inner}</italic>', 1)
            applied.append({"type": "formatting_wrong", "original_tag": "bold", "new_tag": "italic", "text": inner})

    # Change highlight colors
    hl_matches = list(re.finditer(r'<highlight color="(\w+)">(.*?)</highlight>', doc, re.DOTALL))
    rng.shuffle(hl_matches)
    for m in hl_matches:
        if len(applied) >= count:
            break
        orig_color = m.group(1)
        inner = m.group(2)
        new_color = pick(rng, [c for c in HIGHLIGHT_COLORS if c != orig_color])
        original = m.group(0)
        if original in doc:
            doc = doc.replace(original, f'<highlight color="{new_color}">{inner}</highlight>', 1)
            applied.append({"type": "formatting_wrong", "original_color": orig_color, "new_color": new_color, "text": inner[:50]})
    return doc, applied


def corrupt_alignment(rng: random.Random, doc: str, count: int) -> Tuple[str, List[dict]]:
    """Change paragraph alignment to wrong value."""
    applied = []
    lines = doc.split("\n")
    p_indices = [i for i, l in enumerate(lines) if 'align="' in l and l.startswith("<p")]
    rng.shuffle(p_indices)
    for idx in p_indices[:count]:
        line = lines[idx]
        am = re.search(r'align="(\w+)"', line)
        if am:
            orig = am.group(1)
            wrong = pick(rng, [v for v in ALIGNMENT_VALUES if v != orig])
            lines[idx] = line.replace(f'align="{orig}"', f'align="{wrong}"', 1)
            applied.append({"type": "alignment", "line": idx, "original": orig, "corrupted": wrong})
    return "\n".join(lines), applied


def corrupt_spacing(rng: random.Random, doc: str, count: int) -> Tuple[str, List[dict]]:
    """Break paragraph spacing — change spacing-after values."""
    applied = []
    lines = doc.split("\n")
    p_indices = [i for i, l in enumerate(lines) if 'spacing-after="' in l]
    rng.shuffle(p_indices)
    for idx in p_indices[:count]:
        line = lines[idx]
        sm = re.search(r'spacing-after="(\d+)"', line)
        if sm:
            orig = sm.group(1)
            wrong = pick(rng, [v for v in SPACING_VALUES if v != orig])
            lines[idx] = line.replace(f'spacing-after="{orig}"', f'spacing-after="{wrong}"', 1)
            applied.append({"type": "spacing", "line": idx, "original": orig, "corrupted": wrong})
    return "\n".join(lines), applied
