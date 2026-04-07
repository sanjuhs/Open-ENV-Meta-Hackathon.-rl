"""Agent tool implementations — the operations the agent can perform on documents."""

import re
from typing import Tuple


def tool_replace(doc: str, target: str, content: str) -> Tuple[str, bool]:
    if target and target in doc:
        return doc.replace(target, content, 1), True
    return doc, False


def tool_regex_replace(doc: str, pattern: str, replacement: str) -> Tuple[str, bool]:
    try:
        new_doc, n = re.subn(pattern, replacement, doc, count=1)
        return new_doc, n > 0
    except re.error:
        return doc, False


def tool_insert(doc: str, position: int, content: str) -> Tuple[str, bool]:
    lines = doc.split("\n")
    if not (content.startswith("<p") or content.startswith("<heading")):
        content = f'<p align="justify" spacing-after="12">{content}</p>'
    if position < 0 or position >= len(lines):
        lines.append(content)
    else:
        lines.insert(position, content)
    return "\n".join(lines), True


def tool_delete(doc: str, target: str) -> Tuple[str, bool]:
    lines = doc.split("\n")
    new_lines = [l for l in lines if target not in l]
    if len(new_lines) == len(lines):
        return doc, False
    return "\n".join(new_lines), True


def tool_move(doc: str, target: str, position: int) -> Tuple[str, bool]:
    lines = doc.split("\n")
    src = None
    for i, l in enumerate(lines):
        if target in l:
            src = i
            break
    if src is None:
        return doc, False
    moved = lines.pop(src)
    if position < 0 or position >= len(lines):
        lines.append(moved)
    else:
        lines.insert(position, moved)
    return "\n".join(lines), True


def tool_format_text(doc: str, target: str, fmt: str) -> Tuple[str, bool]:
    if target not in doc:
        return doc, False
    if fmt in ("bold", "italic", "underline", "strike"):
        return doc.replace(target, f"<{fmt}>{target}</{fmt}>", 1), True
    if fmt == "uppercase":
        return doc.replace(target, target.upper(), 1), True
    if fmt == "lowercase":
        return doc.replace(target, target.lower(), 1), True
    return doc, False


def tool_highlight(doc: str, target: str, color: str = "yellow") -> Tuple[str, bool]:
    if target not in doc:
        return doc, False
    return doc.replace(target, f'<highlight color="{color}">{target}</highlight>', 1), True


def tool_set_alignment(doc: str, line_index: int, alignment: str) -> Tuple[str, bool]:
    lines = doc.split("\n")
    if line_index < 0 or line_index >= len(lines):
        return doc, False
    line = lines[line_index]
    m = re.search(r'align="(\w+)"', line)
    if m:
        lines[line_index] = line.replace(f'align="{m.group(1)}"', f'align="{alignment}"', 1)
        return "\n".join(lines), True
    return doc, False


def tool_set_spacing(doc: str, line_index: int, spacing_after: str) -> Tuple[str, bool]:
    lines = doc.split("\n")
    if line_index < 0 or line_index >= len(lines):
        return doc, False
    line = lines[line_index]
    m = re.search(r'spacing-after="(\d+)"', line)
    if m:
        lines[line_index] = line.replace(f'spacing-after="{m.group(1)}"', f'spacing-after="{spacing_after}"', 1)
        return "\n".join(lines), True
    return doc, False


def tool_clean_junk_chars(doc: str) -> Tuple[str, bool]:
    """Remove all known junk characters."""
    junk = "\u200b\u00ad\ufeff\u200c\u200d\u2028\u2029"
    cleaned = doc
    for ch in junk:
        cleaned = cleaned.replace(ch, "")
    return cleaned, cleaned != doc


def tool_merge_runs(doc: str, line_index: int) -> Tuple[str, bool]:
    """Merge fragmented <run> elements back into plain text."""
    lines = doc.split("\n")
    if line_index < 0 or line_index >= len(lines):
        return doc, False
    line = lines[line_index]
    if "<run" not in line:
        return doc, False
    # Extract all run contents and merge
    merged = re.sub(r'<run[^>]*>(.*?)</run>', r'\1', line)
    if merged != line:
        lines[line_index] = merged
        return "\n".join(lines), True
    return doc, False


def tool_fix_encoding(doc: str, target: str, replacement: str) -> Tuple[str, bool]:
    """Fix encoding issues — smart quotes, dashes, etc."""
    if target in doc:
        return doc.replace(target, replacement), True
    return doc, False


def tool_add_redline(doc: str, target: str, new_text: str, author: str = "Reviewer") -> Tuple[str, bool]:
    """Add track changes markup."""
    if target not in doc:
        return doc, False
    redlined = f'<del author="{author}">{target}</del><ins author="{author}">{new_text}</ins>'
    return doc.replace(target, redlined, 1), True


def tool_accept_change(doc: str, change_text: str) -> Tuple[str, bool]:
    """Accept a tracked insertion (keep ins content, remove del)."""
    # Find and accept an ins/del pair containing change_text
    ins_match = re.search(rf'<del[^>]*>[^<]*</del><ins[^>]*>([^<]*{re.escape(change_text)}[^<]*)</ins>', doc)
    if ins_match:
        original = ins_match.group(0)
        kept = ins_match.group(1)
        return doc.replace(original, kept, 1), True
    # Just accept an <ins> tag
    ins_only = re.search(rf'<ins[^>]*>([^<]*{re.escape(change_text)}[^<]*)</ins>', doc)
    if ins_only:
        return doc.replace(ins_only.group(0), ins_only.group(1), 1), True
    return doc, False


def tool_reject_change(doc: str, change_text: str) -> Tuple[str, bool]:
    """Reject a tracked change (keep del content, remove ins)."""
    del_match = re.search(rf'<del[^>]*>([^<]*{re.escape(change_text)}[^<]*)</del><ins[^>]*>[^<]*</ins>', doc)
    if del_match:
        original = del_match.group(0)
        kept = del_match.group(1)
        return doc.replace(original, kept, 1), True
    return doc, False


def tool_add_comment(doc: str, target: str, comment_text: str, author: str = "Reviewer") -> Tuple[str, bool]:
    if target not in doc:
        return doc, False
    commented = f'<comment author="{author}" text="{comment_text}">{target}</comment>'
    return doc.replace(target, commented, 1), True


TOOL_REGISTRY = {
    "replace": lambda doc, params: tool_replace(doc, params.get("target", ""), params.get("content", "")),
    "regex_replace": lambda doc, params: tool_regex_replace(doc, params.get("pattern", ""), params.get("replacement", "")),
    "insert": lambda doc, params: tool_insert(doc, params.get("position", -1), params.get("content", "")),
    "delete": lambda doc, params: tool_delete(doc, params.get("target", "")),
    "move": lambda doc, params: tool_move(doc, params.get("target", ""), params.get("position", -1)),
    "format_text": lambda doc, params: tool_format_text(doc, params.get("target", ""), params.get("format", "bold")),
    "highlight": lambda doc, params: tool_highlight(doc, params.get("target", ""), params.get("color", "yellow")),
    "set_alignment": lambda doc, params: tool_set_alignment(doc, params.get("line_index", -1), params.get("alignment", "justify")),
    "set_spacing": lambda doc, params: tool_set_spacing(doc, params.get("line_index", -1), params.get("spacing_after", "12")),
    "clean_junk_chars": lambda doc, params: tool_clean_junk_chars(doc),
    "merge_runs": lambda doc, params: tool_merge_runs(doc, params.get("line_index", -1)),
    "fix_encoding": lambda doc, params: tool_fix_encoding(doc, params.get("target", ""), params.get("replacement", "")),
    "add_redline": lambda doc, params: tool_add_redline(doc, params.get("target", ""), params.get("new_text", ""), params.get("author", "Reviewer")),
    "accept_change": lambda doc, params: tool_accept_change(doc, params.get("change_text", "")),
    "reject_change": lambda doc, params: tool_reject_change(doc, params.get("change_text", "")),
    "add_comment": lambda doc, params: tool_add_comment(doc, params.get("target", ""), params.get("comment_text", ""), params.get("author", "Reviewer")),
}


def execute_tool(doc: str, tool_name: str, params: dict) -> Tuple[str, bool]:
    fn = TOOL_REGISTRY.get(tool_name)
    if fn is None:
        return doc, False
    return fn(doc, params)
