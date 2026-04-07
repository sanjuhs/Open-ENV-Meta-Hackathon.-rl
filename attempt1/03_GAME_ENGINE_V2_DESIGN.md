# DocEdit Game V2 — Full Technical Design

## Overview

DocEdit Game V2 is a procedurally generated, multi-scale document editing RL environment. It extends V1 with:
- **Rich OOXML-like formatting** (bold, italic, highlight, strikethrough, alignment, spacing, borders)
- **PDF-to-DOCX artifact simulation** (fragmented runs, junk characters, encoding issues)
- **Image placeholders** (binary-like blobs the agent must navigate around)
- **Track changes / redlining** (`<ins>`, `<del>` markup)
- **Comments and annotations**
- **Windowed navigation** for documents of unlimited size
- **15+ tool types** organized in 5 tiers
- **8 document templates** including legal and pharmaceutical domains
- **12 corruption types** (up from 6 in V1)
- **Multi-seed system**: document seed + corruption seed for full combinatorial variety

---

## 1. Document Representation

### XML Tag System

We use a simplified OOXML-inspired tag system that mirrors real DOCX internals while remaining parseable by LLMs:

```xml
<doc type="legal_contract" pages="47" version="2.1">
  <meta>
    <title>Service Agreement</title>
    <author>Jane Smith</author>
    <date>2026-04-01</date>
  </meta>

  <section id="s1" numbering="roman">
    <heading level="1" align="center" font-size="16" bold="true">
      SERVICE AGREEMENT
    </heading>

    <p align="justify" spacing-after="12" indent-first="36">
      This Service Agreement (the "<bold>Agreement</bold>") is entered into
      as of <underline>April 1, 2026</underline> between
      <bold>Acme Corporation</bold> ("Provider") and
      <bold>Vertex Partners</bold> ("Client").
    </p>

    <p align="justify" spacing-after="12">
      <highlight color="yellow">WHEREAS Provider possesses expertise in
      professional services</highlight> and Client desires to engage Provider;
    </p>

    <!-- Tracked change: deletion -->
    <p>
      The total fee shall be <del author="John Doe" date="2026-03-15">$500,000</del>
      <ins author="John Doe" date="2026-03-15">$750,000</ins> payable in
      three installments.
    </p>

    <!-- Comment -->
    <p>
      <comment id="c1" author="Sarah Lee" date="2026-03-20"
               text="Legal review needed — is this enforceable in Delaware?">
        Either party may terminate this agreement with 30 days written notice.
      </comment>
    </p>

    <!-- Image -->
    <image id="img_001" alt="Company Seal" format="png" width="200" height="200">
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAAXNSR...
    </image>

    <!-- PDF-to-DOCX artifact: fragmented runs -->
    <p>
      <run spacing="-2">Th</run><run spacing="0">is </run><run spacing="-1">par</run>
      <run spacing="0">agra</run><run spacing="-2">ph </run><run spacing="0">was </run>
      <run spacing="-1">conv</run><run spacing="0">erted </run>
      <run spacing="-2">from </run><run spacing="0">PDF.</run>
    </p>
  </section>
</doc>
```

### Tag Reference

#### Structure Tags
| Tag | Attributes | Purpose |
|-----|-----------|---------|
| `<doc>` | type, pages, version | Root document element |
| `<meta>` | — | Document metadata container |
| `<section>` | id, numbering | Page section with numbering config |
| `<heading>` | level, align, font-size, bold, italic | Section headings (1-6) |
| `<p>` | align, spacing-before, spacing-after, indent-first, indent-left, indent-right, line-spacing, border-bottom, border-top | Paragraphs |
| `<list>` | type (bullet/numbered), start | List container |
| `<item>` | level | List item |
| `<table>` | cols, border | Table container |
| `<row>` | — | Table row |
| `<cell>` | colspan, rowspan, width, align, border | Table cell |

#### Inline Formatting Tags
| Tag | Attributes | Purpose |
|-----|-----------|---------|
| `<bold>` | — | Bold text |
| `<italic>` | — | Italic text |
| `<underline>` | style (single/double/wavy) | Underlined text |
| `<strike>` | — | Strikethrough |
| `<highlight>` | color (yellow/green/red/blue/cyan/magenta) | Background highlight |
| `<font>` | family, size, color | Font override |
| `<sup>` | — | Superscript |
| `<sub>` | — | Subscript |

#### Track Changes Tags
| Tag | Attributes | Purpose |
|-----|-----------|---------|
| `<ins>` | author, date | Inserted text (tracked addition) |
| `<del>` | author, date | Deleted text (tracked deletion) |
| `<format-change>` | author, date, property, old, new | Formatting change |

#### Annotation Tags
| Tag | Attributes | Purpose |
|-----|-----------|---------|
| `<comment>` | id, author, date, text | Comment on text range |
| `<bookmark>` | id, name | Named bookmark |

#### Media Tags
| Tag | Attributes | Purpose |
|-----|-----------|---------|
| `<image>` | id, alt, format, width, height | Embedded image with base64 data |
| `<page-break/>` | — | Forced page break |

#### Artifact Tags (simulating PDF-to-DOCX conversion issues)
| Tag | Attributes | Purpose |
|-----|-----------|---------|
| `<run>` | spacing, font-size, font-family | Fragmented text run (PDF artifact) |
| `<junk>` | — | Container for junk characters / binary noise |

---

## 2. Document Templates (8 types)

### Domain: Legal
1. **Contract** — Service agreements, NDAs, licensing deals (30-100 paragraphs)
2. **Affidavit** — Sworn statements with numbered paragraphs, court formatting (20-60 paragraphs)
3. **Case Brief** — Legal analysis with citations, headings, arguments (40-150 paragraphs)
4. **Discovery Response** — Responses to interrogatories, heavily formatted tables (50-200 paragraphs)

### Domain: Pharmaceutical
5. **Drug Label** — FDA-mandated structure: indications, dosage, warnings, adverse reactions (40-120 paragraphs)
6. **Clinical Study Report** — Trial results with complex tables, figures, appendices (100-500 paragraphs)

### Domain: General Business
7. **Business Report** — Executive summaries, findings, charts, recommendations (30-100 paragraphs)
8. **Corporate Filing** — SEC filings, annual reports with financial tables (50-200 paragraphs)

Each template has:
- Realistic structure (correct sections, headings, legal/regulatory boilerplate)
- Domain-specific vocabulary
- Appropriate formatting patterns
- Variable length based on difficulty

---

## 3. Corruption Engine V2 (12 types)

### Tier 1 — Content Corruptions (from V1, enhanced)
| # | Type | What It Does | Parameters |
|---|------|-------------|-----------|
| 1 | `spelling` | Swap words with misspellings (expanded 100+ word dictionary) | count, severity |
| 2 | `case` | Wrong capitalization (headings, names, sentence starts) | count |
| 3 | `names` | Swap person/company/drug names with alternates | count |
| 4 | `punctuation` | Remove/add/alter punctuation | count |
| 5 | `content_delete` | Remove paragraphs | count |
| 6 | `content_insert` | Add junk/irrelevant paragraphs | count |

### Tier 2 — Formatting Corruptions (NEW)
| # | Type | What It Does | Parameters |
|---|------|-------------|-----------|
| 7 | `formatting_strip` | Remove bold/italic/underline/highlight tags | count |
| 8 | `formatting_wrong` | Apply wrong formatting (bold where italic should be, wrong highlight color) | count |
| 9 | `alignment` | Change paragraph alignment (justify→left, center→right) | count |
| 10 | `spacing` | Break paragraph/line spacing (double→single, add huge gaps) | count |

### Tier 3 — Artifact Corruptions (NEW)
| # | Type | What It Does | Parameters |
|---|------|-------------|-----------|
| 11 | `pdf_artifacts` | Fragment paragraphs into `<run>` elements (simulating PDF conversion) | count |
| 12 | `junk_chars` | Insert zero-width spaces, BOMs, control characters, broken encoding | count |

### Corruption Severity Levels

| Level | Name | Corruption Types | Count Range | Document Size |
|-------|------|-----------------|-------------|---------------|
| 1 | Trivial | 1 type (Tier 1 only) | 1-3 | Small (20-50 para) |
| 2 | Easy | 1-2 types (Tier 1) | 3-8 | Small-Medium (30-80 para) |
| 3 | Medium | 2-3 types (Tier 1-2) | 8-20 | Medium (50-150 para) |
| 4 | Hard | 3-5 types (Tier 1-2) | 15-40 | Medium-Large (100-300 para) |
| 5 | Expert | 4-8 types (Tier 1-3) | 30-80 | Large (200-500 para) |
| 6 | Nightmare | 6-12 types (all tiers) | 50-200+ | Mega (500-2000+ para) |

---

## 4. Tool System (Agent Actions)

The agent's action is now a **tool call** with type-specific parameters:

```python
class DocEditAction(Action):
    tool: str              # Tool name from the toolbox
    params: dict           # Tool-specific parameters

# Examples:
# {"tool": "replace", "params": {"target": "Acme Corp", "content": "Vertex Partners"}}
# {"tool": "highlight", "params": {"target": "Section 3.2", "color": "yellow"}}
# {"tool": "scroll_to", "params": {"chunk": 47}}
# {"tool": "merge_runs", "params": {"paragraph": 23}}
# {"tool": "clean_junk_chars", "params": {"scope": "current_chunk"}}
```

### Tool Categories

**Content Tools**: `replace`, `regex_replace`, `insert`, `delete`, `move`
**Format Tools**: `format_text`, `highlight`, `set_alignment`, `set_spacing`, `set_indent`, `set_font`, `set_border`
**Structure Tools**: `set_heading_level`, `add_comment`, `resolve_comment`, `accept_change`, `reject_change`, `add_redline`
**Cleanup Tools**: `clean_junk_chars`, `merge_runs`, `fix_encoding`, `normalize_whitespace`, `replace_image`
**Navigation Tools**: `scroll_to`, `search_forward`, `search_backward`, `get_overview`

---

## 5. Observation Space

```python
class DocEditObservation(Observation):
    # Current view
    document_chunk: str              # Current visible chunk (XML)
    chunk_index: int                 # Current chunk position
    total_chunks: int                # Total chunks in document

    # Context
    chunk_summary_before: str        # Summary of chunks before current view
    chunk_summary_after: str         # Summary of chunks after current view
    document_overview: str           # High-level doc structure (headings + page counts)

    # Task info
    edit_instruction: str            # What needs to be done
    task_difficulty: int             # 1-6 severity level
    doc_type: str                    # Template type
    corruption_types: list           # Which corruptions were applied

    # Progress
    similarity: float                # Overall document similarity to target (0.0-1.0)
    chunk_similarity: float          # Current chunk similarity to target chunk
    steps_remaining: int             # Steps left
    edits_made: int                  # Actions taken
    edits_estimated: int             # Estimated edits needed
    navigation_steps: int            # Steps used for navigation (efficiency metric)

    # Grading
    collateral_damage: float         # % of correct text that was accidentally modified
```

---

## 6. Reward Function V2

```python
# Per-step reward
base_reward = similarity_after - similarity_before

# Bonuses
if chunk_exact_match:
    reward += 0.1                   # chunk completion bonus
if document_exact_match:
    reward += 1.0                   # full document completion bonus

# Penalties
if noop:
    reward -= 0.01                  # wasted step
if collateral_damage_increased:
    reward -= 0.05                  # broke something
if unnecessary_navigation:
    reward -= 0.005                 # scrolled without editing

# Efficiency bonus (at episode end)
if done and similarity > 0.99:
    efficiency = 1.0 - (steps_used / max_steps)
    reward += 0.2 * efficiency      # faster = better

# Final score
score = similarity * (1.0 - collateral_damage)
```

### Why collateral damage matters:

In V1, the agent could theoretically achieve high similarity by making aggressive changes. In V2, we track **collateral damage**: did the agent accidentally modify text that was already correct? This penalizes sloppy editing and rewards surgical precision.

---

## 7. Seed System

Two independent seeds control task generation:

```python
def generate_task(doc_seed: int, corruption_seed: int, difficulty: int) -> Task:
    # doc_seed → determines document template, content, length
    doc_rng = Random(doc_seed)
    document = generate_document(doc_rng, difficulty)

    # corruption_seed → determines which corruptions and where
    corr_rng = Random(corruption_seed)
    corrupted, corruptions = apply_corruptions(corr_rng, document, difficulty)

    return Task(source=corrupted, target=document, corruptions=corruptions)
```

This means:
- Same `doc_seed` with different `corruption_seed` → same document, different corruptions
- Different `doc_seed` with same `corruption_seed` → different document, similar corruption pattern
- Full combinatorial: 2^32 × 2^32 = 2^64 unique tasks

For evaluation, we define fixed tasks:
```python
EVAL_TASKS = {
    "legal_easy":   {"doc_seed": 1001, "corruption_seed": 5001, "difficulty": 2},
    "legal_medium": {"doc_seed": 1002, "corruption_seed": 5002, "difficulty": 4},
    "legal_hard":   {"doc_seed": 1003, "corruption_seed": 5003, "difficulty": 5},
    "pharma_easy":  {"doc_seed": 2001, "corruption_seed": 6001, "difficulty": 2},
    "pharma_hard":  {"doc_seed": 2003, "corruption_seed": 6003, "difficulty": 5},
}
```

---

## 8. Grading / Verification System

Three levels of grading:

### Level 1: Similarity Score (0.0–1.0)
`SequenceMatcher(current_doc, target_doc).ratio()`
Simple but effective for overall progress.

### Level 2: Structural Grading
Check specific properties independently:
- Content correctness: are the right words present?
- Formatting correctness: are tags applied correctly?
- Structure correctness: are headings/sections in right order?
- Artifact removal: are junk chars / fragmented runs cleaned?

```python
score = (
    0.50 * content_similarity +
    0.25 * formatting_similarity +
    0.15 * structure_similarity +
    0.10 * cleanliness_score
)
```

### Level 3: Edit-Specific Grading
For each corruption, check if it was reversed:
```python
corruption_scores = []
for corruption in task.corruptions:
    if corruption.type == "spelling":
        fixed = corruption.original in current_doc
        corruption_scores.append(1.0 if fixed else 0.0)
    elif corruption.type == "formatting_strip":
        tag_present = f"<{corruption.tag}>" in current_doc
        corruption_scores.append(1.0 if tag_present else 0.0)
    # ... etc
edit_accuracy = mean(corruption_scores)
```

---

## 9. Implementation: What We Build for V2

### Project Structure

```
doc_edit_game_v2/
├── openenv.yaml
├── pyproject.toml
├── README.md
├── __init__.py
├── models.py                          # Action + Observation models
├── client.py                          # EnvClient subclass
├── inference.py                       # Baseline inference script
├── game/
│   ├── __init__.py
│   ├── templates/                     # Document template generators
│   │   ├── __init__.py
│   │   ├── legal_contract.py
│   │   ├── affidavit.py
│   │   ├── case_brief.py
│   │   ├── discovery_response.py
│   │   ├── drug_label.py
│   │   ├── clinical_study_report.py
│   │   ├── business_report.py
│   │   └── corporate_filing.py
│   ├── corruptions/                   # Corruption engine
│   │   ├── __init__.py
│   │   ├── content.py                 # Tier 1: spelling, case, names, punctuation, content
│   │   ├── formatting.py             # Tier 2: format strip/wrong, alignment, spacing
│   │   └── artifacts.py              # Tier 3: PDF artifacts, junk chars
│   ├── tools/                         # Agent tool implementations
│   │   ├── __init__.py
│   │   ├── content_tools.py           # replace, regex_replace, insert, delete, move
│   │   ├── format_tools.py            # format_text, highlight, alignment, spacing, etc.
│   │   ├── structure_tools.py         # headings, comments, redlines, track changes
│   │   ├── cleanup_tools.py           # clean_junk, merge_runs, fix_encoding
│   │   └── navigation_tools.py        # scroll_to, search, overview
│   ├── content_pools.py               # Names, phrases, domain vocabulary
│   ├── generator.py                   # Task generation orchestrator
│   ├── grader.py                      # Multi-level grading system
│   └── windowing.py                   # Document chunking + navigation
└── server/
    ├── __init__.py
    ├── doc_edit_game_v2_environment.py
    ├── app.py
    └── Dockerfile
```

### What's New vs V1:
- 8 document templates (up from 5)
- 12 corruption types (up from 6)
- 20+ tools (up from 5 operations)
- Windowed navigation for large documents
- Rich formatting tags (bold, italic, highlight, strikethrough, alignment, spacing, borders)
- Track changes / redlining
- Comments / annotations
- Image placeholders
- PDF-to-DOCX artifact simulation
- Multi-level grading (similarity + structural + edit-specific)
- Collateral damage tracking
- Dual-seed system (doc_seed + corruption_seed)
- 6 difficulty levels (up from 3)

### What We Scope In for Competition Submission (MVP):
Given time constraints, we prioritize:
1. All 8 document templates ✓
2. All 12 corruption types ✓
3. Core tools: replace, insert, delete, format_text, highlight, clean_junk_chars, merge_runs ✓
4. Windowing (chunk-based) for large documents ✓
5. Multi-level grading ✓
6. 5 fixed evaluation tasks ✓
7. Inference script ✓
8. HF deployment ✓

### What We Defer:
- Full regex_replace (complex to grade)
- Image replacement (interesting but not core to the editing story)
- Full page layout tools (margins, headers/footers)
- Stage 5 curriculum (mixed real-world scenarios)

---

## 10. Competitive Differentiation

| Feature | V1 (r3) | V2 (r4) | Why It Matters |
|---------|---------|---------|---------------|
| Document types | 5 generic | 8 domain-specific (legal + pharma) | Real-world grounding |
| Corruption types | 6 | 12 | Trains more diverse capabilities |
| Formatting | Basic (bold only) | Full (bold/italic/underline/highlight/strike/align/spacing) | Real docs are heavily formatted |
| PDF artifacts | None | Fragmented runs + junk chars | The #1 real-world data quality issue |
| Track changes | None | `<ins>`, `<del>`, accept/reject | Core legal workflow |
| Comments | None | Add/resolve annotations | Core review workflow |
| Document scale | Small (5-40 para) | Small to Mega (20-2000+ para) | Real documents are huge |
| Navigation | See entire doc | Windowed chunks + search | Required for large docs |
| Tools | 5 operations | 20+ specialized tools | Fine-grained control |
| Grading | Similarity only | Similarity + structural + edit-specific + collateral | Nuanced evaluation |
| Seeds | Single seed | Dual seed (doc + corruption) | Combinatorial variety |
| Difficulty levels | 3 | 6 | Smooth curriculum |
