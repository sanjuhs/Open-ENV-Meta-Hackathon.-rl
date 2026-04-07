from .content import corrupt_spelling, corrupt_case, corrupt_names, corrupt_punctuation, corrupt_content_delete, corrupt_content_insert
from .formatting import corrupt_formatting_strip, corrupt_formatting_wrong, corrupt_alignment, corrupt_spacing
from .artifacts import corrupt_pdf_artifacts, corrupt_junk_chars

ALL_CORRUPTIONS = {
    # Tier 1 — Content
    "spelling": corrupt_spelling,
    "case": corrupt_case,
    "names": corrupt_names,
    "punctuation": corrupt_punctuation,
    "content_delete": corrupt_content_delete,
    "content_insert": corrupt_content_insert,
    # Tier 2 — Formatting
    "formatting_strip": corrupt_formatting_strip,
    "formatting_wrong": corrupt_formatting_wrong,
    "alignment": corrupt_alignment,
    "spacing": corrupt_spacing,
    # Tier 3 — Artifacts
    "pdf_artifacts": corrupt_pdf_artifacts,
    "junk_chars": corrupt_junk_chars,
}

TIER_1 = ["spelling", "case", "names", "punctuation", "content_delete", "content_insert"]
TIER_2 = ["formatting_strip", "formatting_wrong", "alignment", "spacing"]
TIER_3 = ["pdf_artifacts", "junk_chars"]
