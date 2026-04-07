# The Applicator Model: Architecture, Tools, and How It Works

## What Is an Applicator Model?

An applicator model is a **small, fast, specialized language model (1B-7B parameters)** trained to execute precise document edits given explicit instructions. It doesn't decide WHAT to edit — a frontier model or a human does that. It decides HOW to edit, using a toolbox of editing operations.

**Analogy**: In software engineering, the "architect" designs the system, and the "builder" implements it. GPT-4o is the architect; the applicator model is the builder. Or: Cursor's AI decides what code changes to make, then a specialized "apply" model executes the diff. We're building the training ground for that "apply" model, but for documents instead of code.

### Real-world examples of the pattern:

| Product | Planner (Frontier) | Applicator (Fast) |
|---------|-------------------|-------------------|
| Cursor | Claude/GPT-4o decides code changes | Fast apply model writes the diff |
| GitHub Copilot | GPT-4o plans code edits | Specialized model applies them |
| This project | Any LLM decides document edits | Our RL-trained model executes them |

---

## How the Applicator Model Works in Practice

### Input (what the model receives):

```json
{
  "document_chunk": "<w:p><w:r><w:t>The Company, hereinafter referred to as Acme Corporation...</w:t></w:r></w:p>",
  "edit_instruction": "Replace 'Acme Corporation' with 'Vertex Partners' in this chunk",
  "chunk_index": 47,
  "total_chunks": 312,
  "context": {
    "document_type": "legal_contract",
    "previous_edits": ["Replaced Acme in chunk 12", "Replaced Acme in chunk 23"],
    "remaining_edits": 15
  }
}
```

### Output (what the model produces):

```json
{
  "tool": "replace",
  "target": "Acme Corporation",
  "content": "Vertex Partners",
  "confidence": 0.98
}
```

### The model then:
1. Calls the `replace` tool with the given parameters
2. The tool executes the edit on the document chunk
3. A verifier checks: did the edit work? Did it break anything?
4. If yes → move to next edit. If no → try again or escalate.

---

## The Tool System

The applicator model doesn't output raw text. It selects and parameterizes **tools**. This is critical because:

1. **Precision**: Tools guarantee syntactically valid output (no hallucinated XML)
2. **Verifiability**: Every tool call is logged and reversible
3. **Composability**: Complex edits = sequences of simple tool calls
4. **Training signal**: Each tool call gets its own reward, enabling fine-grained RL

### Core Tools (Tier 1 — text content):

| Tool | Parameters | What It Does | Example |
|------|-----------|-------------|---------|
| `replace` | target, content | Find exact text, replace with new text | Replace "Acme" with "Vertex" |
| `regex_replace` | pattern, replacement | Regex find-replace | Fix all dates matching `\d{2}/\d{2}/\d{4}` |
| `insert` | position, content | Insert new paragraph at index | Add a clause after paragraph 47 |
| `delete` | target | Delete paragraph containing target | Remove the junk paragraph |
| `move` | target, position | Move paragraph to new position | Move clause 3 to after clause 7 |

### Formatting Tools (Tier 2 — appearance):

| Tool | Parameters | What It Does | Example |
|------|-----------|-------------|---------|
| `format_text` | target, bold/italic/underline/strike | Apply character formatting | Bold the party names |
| `highlight` | target, color | Apply highlight color | Yellow-highlight disputed clause |
| `set_alignment` | target, alignment | Left/center/right/justify | Center the title |
| `set_spacing` | target, before/after/line | Paragraph spacing | Double-space the body text |
| `set_indent` | target, left/right/first_line | Paragraph indentation | Indent numbered paragraphs |
| `set_font` | target, family/size/color | Font properties | Change heading to 14pt Arial |
| `set_border` | target, sides/style/width | Paragraph/page borders | Add bottom border to heading |

### Structural Tools (Tier 3 — document structure):

| Tool | Parameters | What It Does | Example |
|------|-----------|-------------|---------|
| `set_heading_level` | target, level | Change heading level | Promote to Heading 1 |
| `set_page_numbering` | format, start | Restart page numbering | Roman numerals for TOC |
| `add_comment` | target, text, author | Add a comment annotation | Flag clause for review |
| `resolve_comment` | comment_id | Mark comment as resolved | Accept reviewer feedback |
| `accept_change` | change_id | Accept a tracked change | Accept the proposed edit |
| `reject_change` | change_id | Reject a tracked change | Reject the proposed edit |
| `add_redline` | target, new_text | Insert tracked change markup | Show the proposed revision |

### Cleanup Tools (Tier 4 — fixing artifacts):

| Tool | Parameters | What It Does | Example |
|------|-----------|-------------|---------|
| `clean_junk_chars` | target_chars | Remove specified junk characters | Remove zero-width spaces |
| `merge_runs` | paragraph_index | Consolidate fragmented XML runs | Fix PDF-to-DOCX artifacts |
| `fix_encoding` | target, encoding | Fix character encoding issues | Smart quotes to straight |
| `normalize_whitespace` | scope | Fix spacing issues | Remove double spaces |
| `replace_image` | image_id, new_image_ref | Swap an image reference | Update company logo |

### Navigation Tools (Tier 5 — for large documents):

| Tool | Parameters | What It Does | Example |
|------|-----------|-------------|---------|
| `scroll_to` | chunk_index | Move view to a chunk | Go to chunk 150 |
| `search_forward` | query | Find next occurrence | Find next "Acme" |
| `search_backward` | query | Find previous occurrence | Find previous "Acme" |
| `get_chunk_info` | chunk_index | Get metadata about a chunk | What's in chunk 200? |

---

## Windowing System for Infinite-Context Documents

The key innovation for handling 1000+ page documents: **the agent doesn't see the whole document at once**. It works through a **sliding window**.

```
Document (10,000 paragraphs):
┌──────────────────────────────────────────────────────────┐
│ [chunk 0] [chunk 1] [chunk 2] ... [chunk 198] [chunk 199]│
└──────────────────────────────────────────────────────────┘
                          ▲
                    Agent's view
                  ┌──────────┐
                  │ chunk 47  │ ← current (full detail)
                  │ chunk 48  │ ← next (full detail)
                  │ chunk 49  │ ← next (full detail)
                  └──────────┘
                  + summary of chunks 0-46 (condensed)
                  + summary of chunks 50-199 (condensed)
```

### How it works:

1. **Chunk size**: 50 paragraphs per chunk (configurable)
2. **Window size**: 3 chunks visible at a time (150 paragraphs)
3. **Context**: Agent also sees:
   - Document metadata (type, total chunks, current position)
   - Summary of surrounding chunks (section headings, key entities)
   - Edit instruction + which edits are done / remaining
4. **Navigation**: Agent uses `scroll_to`, `search_forward`, `search_backward` to move through the document
5. **Edit scope**: Agent can only edit within visible chunks

This means a 10,000-page document with 50,000 paragraphs = 1,000 chunks. The agent processes it in passes, scrolling through and making edits where needed. This is exactly how human editors work — you don't read the whole document at once, you navigate to sections that need changes.

### Why this works for RL:

- The agent learns an efficient **navigation policy**: go to the right chunk, make the edit, move on
- Reward for finding the right chunk + making the right edit
- Penalty for unnecessary scrolling (wasted steps)
- The agent learns to use `search_forward` to jump to relevant sections instead of scrolling linearly

---

## Training Curriculum

The applicator model is trained in stages of increasing difficulty:

### Stage 1: Single Edits on Small Documents
- 5-20 paragraph documents
- One corruption
- One tool needed
- Agent learns basic tool usage

### Stage 2: Multiple Edits on Medium Documents
- 50-200 paragraph documents
- 5-15 corruptions of 2-3 types
- Agent learns to sequence tool calls
- Agent learns to not break things

### Stage 3: Complex Edits on Large Documents with Formatting
- 200-1000 paragraph documents with rich formatting
- 15-50 corruptions of 4-6 types including formatting and structure
- Agent learns formatting tools
- Agent learns to handle fragmented XML runs

### Stage 4: Full-Scale Documents with Navigation
- 1000-10000+ paragraph documents
- 50-200 corruptions across the entire document
- Agent learns windowed navigation
- Agent learns efficient search strategies
- Agent learns to handle PDF-to-DOCX artifacts, images, junk characters

### Stage 5: Real-World Mixed Scenarios
- Mixed document types (legal, pharma, business)
- Combination of all corruption types
- Time pressure (step limits proportional to optimal edits)
- Partial information (some corruptions not described in instruction, agent must discover them)

---

## Metrics That Matter

| Metric | Definition | Target |
|--------|-----------|--------|
| **Edit accuracy** | % of edits correctly applied | >99% for simple, >95% for complex |
| **Collateral damage** | % of document unchanged that was accidentally modified | <0.1% |
| **Efficiency** | Edits per step (including navigation) | >0.8 for small docs, >0.5 for large |
| **Coverage** | % of required edits completed | >95% |
| **Speed** | Wall-clock time per edit | <100ms per tool call |
| **Cost** | Inference cost per edit | <$0.001 |

---

## Why This Wins the Competition

1. **Real-world utility (30%)**: This is not a toy problem. Legal and pharma companies spend millions on document editing. The applicator model architecture is how the industry will solve it.

2. **Task & grader quality (25%)**: Procedural generation means unlimited training data. The grading is objective (similarity to target) and accounts for collateral damage. Multiple corruption types test different capabilities.

3. **Environment design (20%)**: The windowing system for large documents, the rich tool system, the multi-stage curriculum — this is genuinely novel infrastructure for RL training.

4. **Creativity (10%)**: No one else is building a document editing game with PDF-to-DOCX artifact simulation, redlining, image handling, and infinite-context windowing.
