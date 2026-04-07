# DocEdit V3: Design Exploration for Real-Document RL Environments

## Executive Summary

The current `doc_edit_game_v2` generates toy XML documents (50–200 lines) from content pools.
Real legal, pharma, and corporate documents run **7,000–50,000 lines** across **50–150 pages**, with complex tables, mixed fonts, cross-references, and PDF-specific artifacts.
An agent trained on v2 would not transfer to real document work.

This document explores **six candidate architectures** for a next-generation environment that handles real-scale PDFs, evaluates them against competition scoring and production viability, and recommends a concrete approach.

---

## 1. Current State: Measured Reality

### 1.1 Actual PDF Metrics (from our sample corpus)

| Document | Pages | Chars | Lines | Blocks | Tables | Fonts | Parse Time |
|---|---:|---:|---:|---:|---:|---:|---:|
| Ozempic FDA Label | 53 | 131,500 | 7,046 | 1,876 | 33 | 79 | 2.4s |
| Humira FDA Label | 112 | 240,417 | 12,262 | 2,766 | 31 | 46 | 3.7s |
| Tax Reassessment | 61 | 7,125 | 131 | 191 | 0 | 6 | 11.4s |
| Reliance Annual Report | 146 | 926,790 | 48,677 | 11,712 | 424 | 118 | 33.0s |

Key observations:
- **Scale varies 100x**: The tax filing has 131 lines; the annual report has 48,677.
- **Tables are dominant** in corporate docs (424 tables in Reliance AR).
- **Font diversity** is extreme in pharma (79 fonts for Ozempic — bold, italic, superscript, symbol, etc.).
- **Parse time scales linearly** with page count; the 146-page Reliance doc takes 33s.

### 1.2 What V2 Produces vs. What's Needed

| Dimension | V2 (current) | Real Documents |
|---|---|---|
| Document size | 50–200 lines | 2,000–50,000 lines |
| Structure | Flat XML with `<heading>`, `<paragraph>` | Hierarchical sections, nested tables, footnotes, headers/footers, cross-references |
| Formatting | 4 inline tags (`<bold>`, `<italic>`, `<underline>`, `<highlight>`) | 50–120 distinct font/size/color combinations per document |
| Content | Template pool (~300 phrases) | Domain-specific terminology running to thousands of unique terms |
| Corruption types | 12 synthetic types | OCR artifacts, column merge errors, encoding issues, run fragmentation, table cell shifts |
| Navigation | Window-based (view N lines) | Page-based, section-based, search-based; must handle non-linear reading patterns |
| Grading | String diff against known target | Must handle equivalent representations (e.g., "12,500" vs "12500") |

### 1.3 PyMuPDF Redaction Reality Check

We tested pymupdf's search-and-redact on the Ozempic PDF:
- **Search**: `page.search_for("semaglutide")` correctly finds text rect positions.
- **Redact**: `page.add_redact_annot(rect, text="REPLACED_DRUG")` works but:
  - **Destroys original formatting** — replacement text uses a flat monospace font; original bold/italic/color is lost.
  - **Positioning is fragile** — text can overflow or underflow the original rect, especially for different-length replacements.
  - **Multi-line spans break** — when a search term crosses line boundaries, the redaction rect may only cover part.
  - On page 0 of Ozempic, 5 instances found, 2 redacted → 3 still present. This is because spans can be fragmented across runs, and `search_for` sometimes returns rects that don't fully cover the glyph sequence.

**Verdict**: pymupdf redaction is usable for *controlled* text replacement but unreliable for production PDF editing. Fine for creating corruptions, not for agent-driven edits that must be pixel-accurate.

---

## 2. Six Candidate Architectures

### Architecture A: Direct PDF Editor

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Real PDF     │───▶│  pymupdf      │───▶│  Corrupted   │
│  (seed doc)   │    │  redact/      │    │  PDF         │
│               │    │  insert/      │    │              │
└──────────────┘    │  reorder      │    └──────┬───────┘
                    └──────────────┘           │
                                               ▼
                                    ┌──────────────────┐
                                    │  Agent sees:      │
                                    │  - Page image     │
                                    │  - Extracted text  │
                                    │  Actions:          │
                                    │  - search(term)    │
                                    │  - redact(rect)    │
                                    │  - insert(pos,txt) │
                                    │  - goto_page(n)    │
                                    └──────────────────┘
```

**How it works**: Start with a real PDF. Apply corruptions (redact-and-replace, insert junk pages, swap table columns) using pymupdf. The agent receives page images + extracted text as observations and issues pymupdf operations as actions.

**Grading**: Compare the agent's output PDF against the original, page-by-page, using text extraction diff + visual similarity (SSIM on rendered page images).

| Aspect | Assessment |
|---|---|
| Realism | **Highest** — agent works on actual PDFs |
| Scale | Natural — works on any PDF regardless of length |
| Grading difficulty | **Hard** — equivalent representations, layout shifts, font substitutions make exact matching fragile |
| Engineering effort | Medium (pymupdf does heavy lifting) |
| Competition fit | Risk: grading is noisy; hard to get 0–1 reward signal |
| Agent observation | Page images are expensive (vision model needed) or text extraction is lossy |

**Killer problem**: Grading. If the agent replaces "semaglutide" with the correct text but pymupdf uses a different font, the visual diff penalizes a correct edit. Text-only comparison misses formatting. You need a grading function that understands *semantic equivalence*, which is itself an LLM call — and then you're grading the agent with another agent.

---

### Architecture B: PDF → DOCX Pipeline

```
┌────────┐   pdf2docx   ┌────────┐   corrupt   ┌────────┐
│  PDF   │─────────────▶│  DOCX  │────────────▶│  DOCX' │
└────────┘              └────────┘              └───┬────┘
                                                    │
                         ┌──────────────────────────┘
                         ▼
              ┌─────────────────────┐
              │  Agent sees: DOCX   │
              │  Actions: python-   │
              │  docx operations    │
              │  (replace_text,     │
              │   format_run,       │
              │   insert_paragraph) │
              └─────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  Grade: diff DOCX'  │
              │  against original   │
              │  DOCX (run-level)   │
              └─────────────────────┘
```

**How it works**: Convert the real PDF to DOCX using `pdf2docx` (or `libreoffice --convert-to docx`). The DOCX becomes the ground truth. Apply corruptions to the DOCX (python-docx can add/remove/modify runs, paragraphs, table cells). Agent edits the corrupted DOCX. Grade by diffing paragraph-level and run-level content against the clean DOCX.

**Grading**: python-docx gives structured access — paragraphs, runs with font properties, tables with cells. Diff at run granularity is tractable.

| Aspect | Assessment |
|---|---|
| Realism | **Medium** — DOCX is a real format, but pdf2docx conversion is lossy (especially for complex layouts, scanned PDFs, multi-column) |
| Scale | Good — python-docx handles large docs fine |
| Grading difficulty | **Medium** — structured comparison at run level is doable |
| Engineering effort | High (pdf2docx is fragile; format round-trip loses data) |
| Competition fit | Good grading, but the conversion step adds noise |
| Agent observation | DOCX XML is extremely verbose (~10x the readable text) |

**Killer problem**: `pdf2docx` conversion fidelity. Testing on Reliance AR (146 pages, complex tables, multi-column): conversion produces a DOCX with mangled tables, lost footnotes, and merged columns. The "ground truth" DOCX is already wrong, so the agent is being trained to restore an incorrect version.

---

### Architecture C: Real Content + Scaled XML (Enhanced V2)

```
┌─────────────┐   extract    ┌──────────────┐   stitch   ┌────────────────┐
│  Real PDFs  │────────────▶│  Content DB   │──────────▶│  2000+ line    │
│  (corpus)   │             │  (paragraphs, │           │  XML document  │
└─────────────┘             │   tables,     │           │  (same V2 API) │
                            │   headers)    │           └───────┬────────┘
                            └──────────────┘                    │
                                                                ▼
                                                 ┌──────────────────────────┐
                                                 │  Same V2 corruption      │
                                                 │  engine + new PDF-       │
                                                 │  specific corruptions    │
                                                 │                          │
                                                 │  Same V2 agent API       │
                                                 │  (window-based editing)  │
                                                 └──────────────────────────┘
```

**How it works**: Extract real paragraphs, headings, table rows, and footnotes from our PDF corpus. Store them in a structured content database. At task generation time, compose a document by sampling real content chunks, stitching them into a V2-style XML document with hierarchical sections — but now the document is 2,000–10,000 lines instead of 100.

**Grading**: Same as V2 — we generated both the target and the corrupted version, so we have exact ground truth. String diff works perfectly.

| Aspect | Assessment |
|---|---|
| Realism | **Medium-High** — content is real; structure is still XML but much richer |
| Scale | **Excellent** — parametric control over document size |
| Grading difficulty | **Low** — same target-vs-source diff as V2 |
| Engineering effort | Low-Medium (extend existing V2 codebase) |
| Competition fit | **Strong** — easy grading, scales well, real content |
| Agent observation | Same windowed view, but window management becomes the bottleneck at 10K lines |

**Key challenge**: Navigation. At 10,000 lines with a 100-line window, the agent makes ~100 scroll actions per task just to read the document. This is where a **hierarchical observation** becomes critical:
- Outline view (section headings with line numbers)
- Search results (find text, get line numbers)
- Jump-to-section / jump-to-line

This is the cheapest path to a dramatically more realistic environment.

---

### Architecture D: PDF Viewer Agent (Visual)

```
┌─────────────────────────────────────────────────┐
│                  Browser / Viewer                │
│  ┌──────────────────────┐  ┌──────────────────┐ │
│  │  pdf.js renderer     │  │  Edit panel      │ │
│  │  (page image)        │  │  (text tools)    │ │
│  │                      │  │                  │ │
│  │  Agent sees rendered │  │  Agent actions:  │ │
│  │  page as screenshot  │  │  - click(x,y)   │ │
│  │                      │  │  - type(text)    │ │
│  │                      │  │  - select_range  │ │
│  │                      │  │  - delete        │ │
│  └──────────────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────┐
│  pymupdf backend applies    │
│  edits to actual PDF bytes  │
└─────────────────────────────┘
```

**How it works**: Build a PDF viewer with an editing UI. The agent receives screenshots (or DOM-like structured output) and interacts via mouse/keyboard actions. Backend applies edits via pymupdf. This is the closest to how a human actually edits PDFs.

**Grading**: Visual diff of rendered pages, or text extraction diff.

| Aspect | Assessment |
|---|---|
| Realism | **Maximum** — this IS a PDF editor |
| Scale | Natural |
| Grading difficulty | **Very hard** — visual grading is noisy |
| Engineering effort | **Very high** (full PDF editor UI + screenshot-based agent) |
| Competition fit | **Poor** — too complex for competition scope; requires vision model |
| Agent observation | Screenshots require GPT-4V or similar; expensive per step |

**Killer problem**: This is building Adobe Acrobat. Competition gives us days, not months. The vision-model dependency makes each agent step expensive and slow. Not viable for a competition submission, but a legitimate long-term product architecture.

---

### Architecture E: Chunked Structured JSON

```
┌─────────────┐   parse    ┌───────────────────────────────┐
│  Real PDF   │──────────▶│  Structured JSON               │
└─────────────┘           │  {                              │
                          │    "sections": [                │
                          │      { "heading": "...",        │
                          │        "level": 2,              │
                          │        "paragraphs": [          │
                          │          { "text": "...",       │
                          │            "font": "Arial",     │
                          │            "bold": true,        │
                          │            "footnote_ref": 3 }  │
                          │        ],                       │
                          │        "tables": [ ... ]        │
                          │      }                          │
                          │    ]                            │
                          │  }                              │
                          └──────────────┬──────────────────┘
                                         │
                                         ▼
                          ┌──────────────────────────────┐
                          │  Agent actions: JSON patches  │
                          │  - replace(path, value)       │
                          │  - insert(path, value)        │
                          │  - delete(path)               │
                          │  - move(from_path, to_path)   │
                          └──────────────────────────────┘
```

**How it works**: Parse each PDF into a structured JSON AST preserving hierarchy (sections → paragraphs → runs with formatting metadata). Corruptions modify the JSON tree (alter text, drop fields, shuffle tables). Agent operates via JSON Patch (RFC 6902) operations. Grade by diff against the clean JSON AST.

| Aspect | Assessment |
|---|---|
| Realism | **Medium** — JSON is a proxy format, not the actual document |
| Scale | Good — JSON handles large structures well; chunking by section is natural |
| Grading difficulty | **Low** — JSON diff is deterministic and exact |
| Engineering effort | Medium (parsing is the hard part; JSON patch is well-defined) |
| Competition fit | **Good** — precise grading, structured actions |
| Agent observation | JSON is verbose but LLM-native; can chunk by section |

**Key challenge**: The parse step. Extracting a faithful JSON AST from a PDF that preserves heading hierarchy, table structure, and formatting is a hard problem. pymupdf gives blocks/lines/spans but doesn't know what's a section heading vs. a bold paragraph. You'd need heuristics or an LLM call at parse time — which means the "ground truth" is also noisy.

**Mitigation**: Don't parse real PDFs live. Pre-extract and hand-validate a corpus of JSON ASTs. Ship them as static seed documents. The environment draws from this pre-parsed pool rather than parsing at runtime.

---

### Architecture F: Hybrid — Real PDF Content + Synthetic Corruptions (Recommended)

```
                    ┌────────────────────────────────────┐
                    │        CONTENT LAYER               │
                    │                                    │
┌──────────┐       │  ┌──────────────────────────────┐  │
│  Real    │parse──▶│  │  Structured Content Pool     │  │
│  PDFs    │       │  │  - section_heading[]          │  │
│  (seed   │       │  │  - paragraph[]                │  │
│  corpus) │       │  │  - table_row[]                │  │
└──────────┘       │  │  - footnote[]                 │  │
                    │  │  - cross_reference[]          │  │
                    │  │  + font metadata per chunk    │  │
                    │  └──────────────┬───────────────┘  │
                    │                 │                   │
                    └─────────────────┼───────────────────┘
                                      │
                                      ▼
                    ┌────────────────────────────────────┐
                    │        DOCUMENT ASSEMBLY           │
                    │                                    │
                    │  1. Pick domain (pharma/legal/corp)│
                    │  2. Sample section headings        │
                    │  3. Fill with real paragraphs      │
                    │  4. Insert tables from pool        │
                    │  5. Add cross-refs, footnotes      │
                    │  6. Apply formatting metadata      │
                    │  → Output: rich XML (2K-20K lines) │
                    │                                    │
                    └──────────────────┬─────────────────┘
                                       │
                                       ▼
                    ┌────────────────────────────────────┐
                    │        CORRUPTION ENGINE           │
                    │                                    │
                    │  V2 corruptions (12 types)         │
                    │  + NEW PDF-realistic corruptions:  │
                    │    - OCR error patterns            │
                    │    - Column merge artifacts        │
                    │    - Encoding mangling (UTF→ASCII) │
                    │    - Table cell shift              │
                    │    - Header/footer bleed           │
                    │    - Run fragmentation             │
                    │    - Footnote displacement         │
                    │    - Cross-reference breakage      │
                    │                                    │
                    └──────────────────┬─────────────────┘
                                       │
                                       ▼
                    ┌────────────────────────────────────┐
                    │        AGENT INTERFACE             │
                    │                                    │
                    │  Observation:                      │
                    │    - outline (section→line map)    │
                    │    - window (N-line view)          │
                    │    - search results                │
                    │    - metadata (domain, difficulty)  │
                    │                                    │
                    │  Actions:                          │
                    │    - scroll_to(line)               │
                    │    - search(pattern)               │
                    │    - replace(line, old, new)       │
                    │    - insert_line(after, content)   │
                    │    - delete_line(line)             │
                    │    - format(line, tag, range)      │
                    │    - submit()                      │
                    │                                    │
                    │  Reward:                           │
                    │    exact diff vs known target      │
                    │    (same V2 grading, just bigger)  │
                    │                                    │
                    └────────────────────────────────────┘
```

**How it works**: Extract real content from PDFs into a structured pool (paragraphs, tables, headings — tagged by domain and formatting metadata). At task time, assemble a large (2K–20K line) XML document from this pool, maintaining realistic section hierarchy and formatting diversity. Apply V2's existing corruption engine plus new PDF-specific corruption types. The agent uses an enriched observation space (outline + search + window) and the same edit actions as V2. Grading remains exact because we have the target document.

This is **Architecture C with more structure and Architecture E's parsing benefits**, while staying within V2's proven grading framework.

| Aspect | Assessment |
|---|---|
| Realism | **High** — real content, realistic corruptions, realistic scale |
| Scale | **Excellent** — parametric control; can generate 100-line to 50K-line docs |
| Grading difficulty | **Low** — same exact-match diff as V2 |
| Engineering effort | **Medium** — builds on V2; biggest work is content extraction + new corruptions |
| Competition fit | **Excellent** — precise rewards, easy validation, scales to hard tasks |
| Agent observation | Rich and LLM-native (text + outline + search); no vision model needed |

---

## 3. Comparison Matrix

| | A: Direct PDF | B: PDF→DOCX | C: Scaled XML | D: Visual | E: JSON Patch | **F: Hybrid** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Realism** | ★★★★★ | ★★★ | ★★★ | ★★★★★ | ★★★ | **★★★★** |
| **Grading precision** | ★★ | ★★★ | ★★★★★ | ★ | ★★★★★ | **★★★★★** |
| **Scale handling** | ★★★★ | ★★★ | ★★★★★ | ★★★★ | ★★★★ | **★★★★★** |
| **Competition scoring** | ★★ | ★★★ | ★★★★ | ★ | ★★★★ | **★★★★★** |
| **Eng. effort (days)** | 3–5 | 5–8 | 2–3 | 15–30 | 4–6 | **3–5** |
| **LLM cost / step** | High (vision) | Low | Low | Very High | Low | **Low** |
| **Reproducibility** | ★★★ | ★★ | ★★★★★ | ★★ | ★★★★ | **★★★★★** |
| **Transfer to prod** | ★★★★★ | ★★ | ★★ | ★★★★★ | ★★★ | **★★★★** |

---

## 4. Deep Dive: Key Design Challenges

### 4.1 Navigation at Scale

At 10,000 lines with a 100-line window, pure scrolling is 100+ actions of overhead per task. The agent needs **structured navigation**:

```
OBSERVATION = {
    "outline": [                           # Always visible
        {"section": "1. INDICATIONS AND USAGE", "line": 45},
        {"section": "1.1 Type 2 Diabetes", "line": 52},
        {"section": "2. DOSAGE AND ADMINISTRATION", "line": 180},
        ...
    ],
    "window": {                            # Current view
        "start_line": 180,
        "end_line": 280,
        "content": "..."                   # 100 lines of text
    },
    "search_results": [                    # From last search action
        {"line": 203, "context": "...semaglutide injection..."},
        {"line": 847, "context": "...semaglutide is contraindicated..."},
    ],
    "metadata": {
        "total_lines": 8542,
        "domain": "pharma",
        "difficulty": 4,
        "corruptions_remaining_estimate": 12
    }
}
```

The `search(pattern)` action is critical — it lets the agent jump directly to corruption sites instead of scanning linearly. An agent that searches first and edits second will dramatically outperform a scrolling agent.

### 4.2 Corruption Realism: PDF-Specific Artifacts

Real PDF→text extraction produces distinctive errors that current V2 doesn't simulate:

| Corruption Type | Example | Mechanism |
|---|---|---|
| **OCR substitution** | `rn` → `m`, `cl` → `d`, `I` → `l` | Character-pair confusion from image-to-text |
| **Column merge** | Two columns read left-to-right as one line | Multi-column PDF extracted as single flow |
| **Run fragmentation** | `<run>se</run><run>maglutide</run>` → should be one run | PDF stores text in arbitrary span boundaries |
| **Encoding mangling** | `§` → `Â§`, `–` → `â€"` | UTF-8 interpreted as Latin-1 or vice versa |
| **Table cell shift** | Misaligned columns in extracted table | Tab/space alignment lost during extraction |
| **Header/footer bleed** | `Page 42 of 146\nSection 3.2 Adverse Reactions` | Header text concatenated with body |
| **Footnote displacement** | Footnote text appears mid-paragraph instead of bottom | Reference marker and content separated |
| **Ligature decomposition** | `fi` → `f i`, `ffi` → `f f i` | Font ligatures decomposed during extraction |
| **Hyphenation artifact** | `sema-\nglutide` → `sema- glutide` | Line-break hyphenation preserved incorrectly |

These can all be implemented as corruption functions in the existing V2 framework. Each is a `(rng, source, count) → (corrupted, corruption_list)` callable.

### 4.3 Reward Design for Partial Credit

V2 uses a single similarity score. At scale, we need **component-based rewards** to give the agent meaningful learning signal:

```python
def compute_reward(source: str, target: str, action_history: list) -> dict:
    # 1. Text accuracy (0.5 weight) — normalized edit distance
    text_sim = 1.0 - (levenshtein(source, target) / max(len(source), len(target)))

    # 2. Edit precision (0.2 weight) — correct edits / total edits
    correct_edits = count_matching_corruptions_fixed(source, target, action_history)
    total_edits = len([a for a in action_history if a["type"] in ("replace", "insert", "delete")])
    precision = correct_edits / max(total_edits, 1)

    # 3. Collateral damage (0.2 weight) — 1 - (unintended changes / total changes)
    unintended = count_unintended_changes(source, target, action_history)
    collateral = 1.0 - min(unintended / max(total_edits, 1), 1.0)

    # 4. Efficiency (0.1 weight) — bonus for fewer steps
    step_ratio = len(action_history) / max_steps
    efficiency = max(0, 1.0 - step_ratio)

    return {
        "total": 0.5 * text_sim + 0.2 * precision + 0.2 * collateral + 0.1 * efficiency,
        "text_similarity": text_sim,
        "edit_precision": precision,
        "collateral_damage_score": collateral,
        "efficiency": efficiency,
    }
```

### 4.4 Content Pool Engineering

The hybrid approach requires a rich, deduplicated content pool. Here's the extraction pipeline:

```
Real PDF → pymupdf blocks → classify (heading/paragraph/table/footnote)
         → deduplicate (MinHash LSH, ~85% similarity threshold)
         → tag (domain, formatting, length bucket)
         → store as JSON lines: {"type": "paragraph", "domain": "pharma",
            "text": "...", "font": "TimesNewRoman", "size": 10, "bold": false,
            "source_doc": "ozempic", "page": 23}
```

From our four PDFs alone:
- ~70,000 usable paragraphs
- ~500 tables (with row/column structure)
- ~200 section headings
- 5 domains (pharma, legal/tax, corporate, regulatory, financial)

With deduplication, this yields ~15,000 unique content chunks — enough to generate thousands of distinct 10K-line documents without repetition.

### 4.5 How Does an Agent Navigate a 150-Page Document?

This is the central UX and RL problem. Three strategies, in increasing sophistication:

**Strategy 1: Instruction-Guided Search** (baseline)
The corruption instruction tells the agent what to fix: "Fix 12 spelling errors including 'semaglutdie' → 'semaglutide'."
Agent searches for each known-bad term, jumps to it, fixes it.
Works for spelling/name/punctuation. Fails for structural corruptions where the instruction can't enumerate every instance.

**Strategy 2: Outline + Systematic Scan**
Agent reads the outline, visits each section in order, compares against expected structure (inferred from section headings), fixes anomalies.
Works for content insertion/deletion, table errors. Slow but thorough.

**Strategy 3: Hierarchical Triage** (optimal)
1. Read outline → identify suspicious section sizes (a section with 3 lines in a drug label's "Adverse Reactions" is likely missing content).
2. Search for known corruption patterns (encoding artifacts, OCR patterns).
3. Spot-check formatting-heavy regions (tables, headers).
4. Fix in priority order: high-impact corruptions first.

The environment should be designed to reward Strategy 3 by making corruption density non-uniform (clustered in certain sections) and by giving partial credit per-corruption-fixed.

---

## 5. New Corruption Types for V3

Beyond V2's 12 types, the following are implementable within the existing framework:

### Tier 4: PDF Extraction Artifacts

```python
def corrupt_ocr_substitution(rng, source, count):
    """Simulate OCR character confusions."""
    OCR_PAIRS = [
        ("rn", "m"), ("cl", "d"), ("I", "l"), ("O", "0"),
        ("1", "l"), ("vv", "w"), ("li", "h"), ("ri", "n"),
    ]
    # Find words containing OCR-pair patterns, replace up to `count`
    ...

def corrupt_column_merge(rng, source, count):
    """Simulate multi-column text extracted as single line."""
    # Find adjacent short lines, merge them with double-space separator
    ...

def corrupt_encoding_mangle(rng, source, count):
    """Simulate UTF-8 → Latin-1 → UTF-8 round-trip damage."""
    ENCODING_MAP = {"§": "Â§", "–": "â€"", "—": "â€"", "'": "â€™", """: "â€œ"}
    ...

def corrupt_run_fragmentation(rng, source, count):
    """Split <run> elements at random positions (PDF span fragmentation)."""
    ...

def corrupt_table_cell_shift(rng, source, count):
    """Shift table cell content one column left/right."""
    ...

def corrupt_footnote_displacement(rng, source, count):
    """Move footnote text from document end into the referencing paragraph."""
    ...

def corrupt_hyphenation_artifact(rng, source, count):
    """Insert line-break hyphens mid-word: 'semaglutide' → 'sema-\\nglutide'."""
    ...

def corrupt_ligature_decomposition(rng, source, count):
    """Decompose common ligatures: 'fi' → 'f i', 'ffl' → 'f f l'."""
    ...
```

These slot directly into V2's tier system and corruption engine.

---

## 6. Extended Observation Space

### 6.1 Outline View

Generated from the document's heading tags:

```xml
<outline>
  <entry level="1" line="1">PRESCRIBING INFORMATION</entry>
  <entry level="2" line="8">1 INDICATIONS AND USAGE</entry>
  <entry level="3" line="12">1.1 Type 2 Diabetes Mellitus</entry>
  <entry level="3" line="45">1.2 Cardiovascular Risk Reduction</entry>
  <entry level="2" line="89">2 DOSAGE AND ADMINISTRATION</entry>
  ...
  <entry level="2" line="4201">17 PATIENT COUNSELING INFORMATION</entry>
</outline>
```

This is ~50 lines even for a 10K-line document. The agent always sees this in every observation, giving it a map of the document.

### 6.2 Search Action

```python
class SearchAction(BaseModel):
    pattern: str           # regex or literal
    case_sensitive: bool = False
    max_results: int = 20

class SearchResult(BaseModel):
    line: int
    column: int
    context: str           # ±2 lines around match
    section: str           # which outline section this falls in
```

### 6.3 Document Statistics

```python
class DocStats(BaseModel):
    total_lines: int
    total_sections: int
    total_tables: int
    total_footnotes: int
    avg_line_length: float
    formatting_tag_count: int
```

---

## 7. Implementation Roadmap (Architecture F)

### Phase 1: Content Extraction (Day 1)

- Parse all sample PDFs into block/line/span structure via pymupdf
- Classify blocks into paragraph, heading, table, footnote
- Deduplicate with MinHash
- Output: `content_pool.jsonl` with tagged chunks

### Phase 2: Document Assembly (Day 1–2)

- Build a `DocumentAssembler` class that:
  - Takes domain, size, seed
  - Samples section headings from pool
  - Fills sections with real paragraphs
  - Inserts tables at appropriate positions
  - Adds cross-references and footnotes
  - Outputs V2-compatible XML (same tag set, same structure)
- Parameterize size: small (500 lines), medium (2K), large (5K), mega (10K+)

### Phase 3: New Corruption Types (Day 2)

- Implement 8 new PDF-specific corruptions (OCR, column merge, encoding, etc.)
- Add as Tier 4 in the corruption engine
- Write unit tests proving each corruption produces fixable damage

### Phase 4: Enhanced Agent Interface (Day 2–3)

- Add `outline` to every observation
- Add `search(pattern)` action → returns search results
- Add `jump_to(line)` action (instant scroll)
- Increase window size option (100 / 200 / 500 lines)
- Update `state()` to include `DocStats`

### Phase 5: Grading Refinements (Day 3)

- Component-based reward (text accuracy, precision, collateral, efficiency)
- Per-corruption tracking (which corruptions were fixed)
- Partial credit for partially correct edits

### Phase 6: Evaluation Tasks (Day 3)

- Design 5+ tasks spanning domains and difficulties:
  1. `pharma_label_easy` — 2K-line drug label, 8 spelling/name errors
  2. `legal_contract_medium` — 5K-line contract, 15 mixed errors + formatting
  3. `tax_assessment_hard` — 3K-line tax order, 20 errors including OCR artifacts
  4. `annual_report_expert` — 10K-line corporate report, 30 errors across tables and text
  5. `multi_domain_nightmare` — 15K-line composite document, 60+ errors, all corruption types

---

## 8. Why Not Direct PDF Editing? (Honest Assessment)

Direct PDF editing (Architecture A) is the most "real" option and would be the strongest product differentiator. Here's why it's not recommended **for the competition** but IS the right long-term play:

### For competition (NO):
- **Grading is intractable without an LLM judge** — font substitution, layout reflow, and equivalent representations make deterministic scoring impossible.
- **pymupdf redaction is lossy** — replaces formatting, doesn't preserve line spacing.
- **Competition rewards need precision** — noisy rewards → bad RL signal → bad scores.

### For production (YES):
- Real users edit real PDFs, not XML
- A product that lets an AI agent fix a 150-page FDA label in-situ is worth building
- The grading problem is solved by human verification (the product is a copilot, not an autograder)
- pymupdf + pikepdf + pdfplumber together cover most editing operations

### Recommended path:
1. **Win the competition** with Architecture F (Hybrid) — precise grading, fast iteration
2. **Build the product** on Architecture A (Direct PDF) — real user value, human-in-the-loop grading
3. Architecture F serves as the **training environment** for agents that deploy on Architecture A

---

## 9. Open Questions

1. **Window size vs. token cost**: A 500-line window at ~15 tokens/line is 7,500 tokens per observation. With 40 steps, that's 300K tokens per task. At GPT-4o-mini rates ($0.15/1M input), that's $0.045 per task. Acceptable, but scales poorly with document size.

2. **Corruption detection vs. corruption fixing**: Should the environment reward finding corruptions (search + report) separately from fixing them? Two-phase tasks might produce better RL signal.

3. **Multi-agent**: Could a "navigator" agent produce a list of suspicious locations, then a "fixer" agent visits each one? This decomposes the long-horizon problem.

4. **Curriculum learning**: Start training on 500-line docs with 3 corruptions, gradually increase to 10K-line docs with 40 corruptions. The environment supports this natively via the difficulty parameter.

5. **Real PDF round-trip**: Even in Architecture F, can we render the final XML back to a PDF (via reportlab or weasyprint) so that the agent's output is a real document? This adds a visual verification step without the grading problems of Architecture A.

---

## 10. Conclusion

**Architecture F (Hybrid)** is the clear winner for competition submission:
- Builds on the proven V2 framework
- Real content from actual PDFs ensures domain authenticity
- Exact grading via target-source diff
- Scales from trivial (500 lines, 3 errors) to nightmare (15K lines, 60 errors)
- New PDF-specific corruptions add realism without sacrificing grading precision
- Enhanced navigation (outline + search) makes large documents tractable for agents

The key insight is that **realism comes from content and corruption patterns, not from the document format itself**. An XML document filled with real FDA label text and corrupted with realistic OCR artifacts is a better RL training environment than an actual PDF with noisy grading.

Build F for the competition. Build A for the product. F trains the agents that A deploys.
