"""Tier 3 — Artifact corruptions: PDF-to-DOCX fragments, junk characters."""

import random
import re
from typing import List, Tuple

from ..content_pools import JUNK_CHARS, pick


def corrupt_pdf_artifacts(rng: random.Random, doc: str, count: int) -> Tuple[str, List[dict]]:
    """Fragment paragraphs into <run> elements simulating PDF-to-DOCX conversion artifacts."""
    lines = doc.split("\n")
    applied = []
    p_indices = [i for i, l in enumerate(lines) if l.startswith("<p") and len(l) > 50]
    rng.shuffle(p_indices)

    for idx in p_indices[:count]:
        line = lines[idx]
        # Extract attributes and text content
        attr_match = re.match(r'(<p[^>]*>)(.*?)(</p>)', line, re.DOTALL)
        if not attr_match:
            continue
        p_open = attr_match.group(1)
        text = attr_match.group(2)
        p_close = attr_match.group(3)

        # Don't fragment lines that already have complex tags
        if "<run" in text or "<table" in text or "<image" in text:
            continue

        # Fragment the text into runs of 2-5 characters
        runs = []
        i = 0
        while i < len(text):
            # Don't split inside tags
            if text[i] == '<':
                end = text.find('>', i)
                if end != -1:
                    tag_end = text.find('>', end + 1) if text[i+1] == '/' else end
                    closing = text.find(f'</', i)
                    if closing > end:
                        runs.append(text[i:text.find('>', closing) + 1])
                        i = text.find('>', closing) + 1
                    else:
                        runs.append(text[i:end + 1])
                        i = end + 1
                    continue

            chunk_size = rng.randint(2, 5)
            chunk = text[i:i+chunk_size]
            if '<' in chunk:
                chunk = text[i:text.index('<', i)]
            if chunk:
                spacing = rng.choice([-2, -1, 0, 0, 1])
                runs.append(f'<run spacing="{spacing}">{chunk}</run>')
            i += max(len(chunk), 1)

        fragmented = "".join(runs)
        lines[idx] = f'{p_open}{fragmented}{p_close}'
        applied.append({"type": "pdf_artifacts", "line": idx, "original_text": text[:60]})

    return "\n".join(lines), applied


def corrupt_junk_chars(rng: random.Random, doc: str, count: int) -> Tuple[str, List[dict]]:
    """Insert zero-width spaces, BOMs, and other invisible junk characters."""
    lines = doc.split("\n")
    applied = []
    p_indices = [i for i, l in enumerate(lines) if l.startswith("<p") and len(l) > 20]
    rng.shuffle(p_indices)

    for idx in p_indices[:count]:
        line = lines[idx]
        # Find text content (not inside tags)
        text_spans = list(re.finditer(r'(?<=>)[^<]{3,}', line))
        if not text_spans:
            continue
        span = rng.choice(text_spans)
        text = span.group()
        # Insert 1-3 junk chars at random positions within the text
        n_junk = rng.randint(1, 3)
        chars_inserted = []
        modified = list(text)
        for _ in range(n_junk):
            pos = rng.randint(0, len(modified) - 1)
            junk = pick(rng, JUNK_CHARS)
            modified.insert(pos, junk)
            chars_inserted.append(repr(junk))
        new_text = "".join(modified)
        lines[idx] = line.replace(text, new_text, 1)
        applied.append({"type": "junk_chars", "line": idx, "chars": chars_inserted})

    return "\n".join(lines), applied
