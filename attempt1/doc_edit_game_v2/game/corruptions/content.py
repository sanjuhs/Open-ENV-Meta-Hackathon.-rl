"""Tier 1 — Content corruptions: spelling, case, names, punctuation, content."""

import random
import re
from typing import List, Tuple

from ..content_pools import (
    ALTERNATE_COMPANIES, ALTERNATE_NAMES, FIRST_NAMES, MISSPELLINGS, pick,
)


def _text_words(document: str) -> List[str]:
    text_only = re.sub(r"<[^>]+>", " ", document)
    return list(set(re.findall(r"\b[a-zA-Z]{4,}\b", text_only)))


def corrupt_spelling(rng: random.Random, doc: str, count: int) -> Tuple[str, List[dict]]:
    words = _text_words(doc)
    corruptible = [w for w in words if w.lower() in MISSPELLINGS]
    rng.shuffle(corruptible)
    applied = []
    for word in corruptible[:count]:
        misspelled = MISSPELLINGS[word.lower()]
        if word[0].isupper():
            misspelled = misspelled[0].upper() + misspelled[1:]
        if word in doc:
            doc = doc.replace(word, misspelled, 1)
            applied.append({"type": "spelling", "original": word, "corrupted": misspelled})
    return doc, applied


def corrupt_case(rng: random.Random, doc: str, count: int) -> Tuple[str, List[dict]]:
    lines = doc.split("\n")
    applied = []
    indices = list(range(len(lines)))
    rng.shuffle(indices)
    for idx in indices:
        if len(applied) >= count:
            break
        line = lines[idx]
        # Lowercase a heading that should be uppercase
        hm = re.match(r'(<heading[^>]*>)(.*?)(</heading>)', line)
        if hm and hm.group(2).isupper():
            orig = hm.group(2)
            lines[idx] = line.replace(orig, orig.lower(), 1)
            applied.append({"type": "case", "original": orig, "corrupted": orig.lower()})
            continue
        # Uppercase random words in paragraphs
        if "<p" in line:
            words = re.findall(r"\b[a-z]{4,}\b", re.sub(r"<[^>]+>", "", line))
            if words:
                w = rng.choice(words)
                if w in line:
                    lines[idx] = line.replace(w, w.upper(), 1)
                    applied.append({"type": "case", "original": w, "corrupted": w.upper()})
    return "\n".join(lines), applied


def corrupt_names(rng: random.Random, doc: str, count: int) -> Tuple[str, List[dict]]:
    applied = []
    for name, alt in ALTERNATE_NAMES.items():
        if len(applied) >= count:
            break
        if name in doc:
            doc = doc.replace(name, alt, 1)
            applied.append({"type": "name", "original": name, "corrupted": alt})
    for company, alt in ALTERNATE_COMPANIES.items():
        if len(applied) >= count:
            break
        if company in doc:
            doc = doc.replace(company, alt, 1)
            applied.append({"type": "name", "original": company, "corrupted": alt})
    return doc, applied


def corrupt_punctuation(rng: random.Random, doc: str, count: int) -> Tuple[str, List[dict]]:
    lines = doc.split("\n")
    applied = []
    indices = list(range(len(lines)))
    rng.shuffle(indices)
    for idx in indices:
        if len(applied) >= count:
            break
        line = lines[idx]
        if not line.startswith("<p"):
            continue
        if line.rstrip().endswith(".</p>"):
            lines[idx] = line.rstrip()[:-5] + "</p>"
            applied.append({"type": "punctuation", "action": "removed_period", "line": idx})
        elif ", " in line and rng.random() < 0.5:
            pos = line.index(", ")
            lines[idx] = line[:pos] + line[pos+1:]
            applied.append({"type": "punctuation", "action": "removed_comma", "line": idx})
    return "\n".join(lines), applied


def corrupt_content_delete(rng: random.Random, doc: str, count: int) -> Tuple[str, List[dict]]:
    lines = doc.split("\n")
    p_indices = [i for i, l in enumerate(lines) if l.startswith("<p") and len(l) > 30]
    rng.shuffle(p_indices)
    applied = []
    for idx in p_indices[:count]:
        deleted = lines[idx]
        lines[idx] = ""
        applied.append({"type": "content_delete", "line": idx, "text": deleted})
    lines = [l for l in lines if l != ""]
    return "\n".join(lines), applied


def corrupt_content_insert(rng: random.Random, doc: str, count: int) -> Tuple[str, List[dict]]:
    lines = doc.split("\n")
    applied = []
    junk_paras = [
        '<p align="justify" spacing-after="12">THIS PARAGRAPH DOES NOT BELONG IN THIS DOCUMENT AND SHOULD BE REMOVED.</p>',
        '<p align="justify" spacing-after="12">[PLACEHOLDER TEXT — DELETE BEFORE FILING]</p>',
        '<p align="justify" spacing-after="12">Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>',
        '<p align="justify" spacing-after="12">NOTE: This section is under review and may contain outdated information. Please verify before distribution.</p>',
    ]
    for i in range(min(count, len(junk_paras))):
        p_indices = [j for j, l in enumerate(lines) if l.startswith("<p")]
        if p_indices:
            pos = rng.choice(p_indices)
            junk = pick(rng, junk_paras)
            lines.insert(pos + 1, junk)
            applied.append({"type": "content_insert", "after_line": pos, "text": junk})
    return "\n".join(lines), applied
