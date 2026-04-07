"""Task generation orchestrator — documents + corruptions + instructions."""

import random
from typing import List

from .templates import TEMPLATES
from .corruptions import ALL_CORRUPTIONS, TIER_1, TIER_2, TIER_3


DIFFICULTY_CONFIG = {
    1: {"name": "trivial", "types_pool": TIER_1[:2], "count": (1, 3), "doc_size": "small", "max_steps": 10},
    2: {"name": "easy", "types_pool": TIER_1, "count": (3, 8), "doc_size": "small", "max_steps": 20},
    3: {"name": "medium", "types_pool": TIER_1 + TIER_2[:2], "count": (8, 15), "doc_size": "medium", "max_steps": 30},
    4: {"name": "hard", "types_pool": TIER_1 + TIER_2, "count": (12, 25), "doc_size": "medium", "max_steps": 40},
    5: {"name": "expert", "types_pool": TIER_1 + TIER_2 + TIER_3, "count": (20, 40), "doc_size": "large", "max_steps": 60},
    6: {"name": "nightmare", "types_pool": TIER_1 + TIER_2 + TIER_3, "count": (35, 80), "doc_size": "mega", "max_steps": 100},
}

# Domain-specific template pools
LEGAL_TEMPLATES = ["legal_contract", "affidavit", "case_brief"]
PHARMA_TEMPLATES = ["drug_label", "clinical_study_report"]
BUSINESS_TEMPLATES = ["business_report"]


def generate_task(doc_seed: int = 0, corruption_seed: int = 0, difficulty: int = 2, domain: str = "any") -> dict:
    """
    Generate a complete task with dual-seed system.

    Args:
        doc_seed: Seed for document generation
        corruption_seed: Seed for corruption application
        difficulty: 1-6 severity level
        domain: "legal", "pharma", "business", or "any"
    """
    diff = DIFFICULTY_CONFIG.get(difficulty, DIFFICULTY_CONFIG[2])
    doc_rng = random.Random(doc_seed)
    corr_rng = random.Random(corruption_seed)

    # Select template based on domain
    if domain == "legal":
        pool = LEGAL_TEMPLATES
    elif domain == "pharma":
        pool = PHARMA_TEMPLATES
    elif domain == "business":
        pool = BUSINESS_TEMPLATES
    else:
        pool = list(TEMPLATES.keys())

    doc_type = doc_rng.choice(pool)
    gen_fn = TEMPLATES[doc_type]
    target = gen_fn(doc_rng, size=diff["doc_size"])

    # Apply corruptions
    total_count = corr_rng.randint(*diff["count"])
    n_types = min(len(diff["types_pool"]), corr_rng.randint(1, min(4, len(diff["types_pool"]))))
    chosen_types = corr_rng.sample(diff["types_pool"], k=n_types)
    per_type = max(1, total_count // len(chosen_types))
    remainder = total_count - per_type * len(chosen_types)

    all_corruptions: List[dict] = []
    source = target

    for i, ctype in enumerate(chosen_types):
        count = per_type + (1 if i < remainder else 0)
        fn = ALL_CORRUPTIONS.get(ctype)
        if fn:
            source, corruptions = fn(corr_rng, source, count)
            all_corruptions.extend(corruptions)

    instruction = _build_instruction(all_corruptions, doc_type)

    return {
        "source": source,
        "target": target,
        "instruction": instruction,
        "doc_type": doc_type,
        "domain": _domain_for_type(doc_type),
        "difficulty": difficulty,
        "difficulty_name": diff["name"],
        "corruption_types_used": chosen_types,
        "corruption_count": len(all_corruptions),
        "corruptions": all_corruptions,
        "max_steps": diff["max_steps"],
        "doc_seed": doc_seed,
        "corruption_seed": corruption_seed,
    }


def _domain_for_type(doc_type: str) -> str:
    if doc_type in LEGAL_TEMPLATES:
        return "legal"
    if doc_type in PHARMA_TEMPLATES:
        return "pharma"
    return "business"


def _build_instruction(corruptions: List[dict], doc_type: str) -> str:
    if not corruptions:
        return "The document appears correct. No edits needed."

    parts = []
    by_type = {}
    for c in corruptions:
        by_type.setdefault(c["type"], []).append(c)

    if "spelling" in by_type:
        items = by_type["spelling"]
        examples = ", ".join(f"'{c['corrupted']}' → '{c['original']}'" for c in items[:3])
        suffix = f" (and {len(items)-3} more)" if len(items) > 3 else ""
        parts.append(f"Fix {len(items)} spelling error(s): {examples}{suffix}.")

    if "case" in by_type:
        parts.append(f"Fix {len(by_type['case'])} capitalization error(s) — some text has incorrect case.")

    if "name" in by_type:
        items = by_type["name"]
        examples = ", ".join(f"'{c['corrupted']}' should be '{c['original']}'" for c in items[:2])
        parts.append(f"Correct {len(items)} wrong name(s)/entity(ies): {examples}.")

    if "punctuation" in by_type:
        parts.append(f"Fix {len(by_type['punctuation'])} punctuation error(s).")

    if "content_delete" in by_type:
        parts.append(f"Restore {len(by_type['content_delete'])} paragraph(s) that were removed from the document.")

    if "content_insert" in by_type:
        parts.append(f"Remove {len(by_type['content_insert'])} junk paragraph(s) that don't belong.")

    if "formatting_strip" in by_type:
        items = by_type["formatting_strip"]
        tags = set(c.get("tag", "bold") for c in items)
        parts.append(f"Restore {len(items)} missing formatting tag(s) ({', '.join(tags)}).")

    if "formatting_wrong" in by_type:
        parts.append(f"Fix {len(by_type['formatting_wrong'])} incorrect formatting tag(s) (wrong type or color).")

    if "alignment" in by_type:
        parts.append(f"Fix {len(by_type['alignment'])} paragraph alignment error(s).")

    if "spacing" in by_type:
        parts.append(f"Fix {len(by_type['spacing'])} paragraph spacing error(s).")

    if "pdf_artifacts" in by_type:
        parts.append(f"Clean up {len(by_type['pdf_artifacts'])} paragraph(s) with PDF-to-DOCX conversion artifacts (fragmented <run> elements that need merging).")

    if "junk_chars" in by_type:
        parts.append(f"Remove invisible junk characters (zero-width spaces, BOMs) from {len(by_type['junk_chars'])} location(s).")

    return " ".join(parts)
