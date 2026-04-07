# Real-World Use Cases: Why Document Editing RL Matters

## The Core Problem

Every day, millions of professionals — lawyers, pharmaceutical regulatory specialists, compliance officers, paralegals, editors — spend hours making precise edits to massive documents. These edits are:

- **High-stakes**: A wrong name in a contract, a missing clause in a regulatory submission, or an incorrect dosage in a drug label can have catastrophic consequences (lawsuits, FDA rejections, patient harm).
- **Tedious**: The same types of changes repeated across 500-2000 page documents — find this name and replace it everywhere, fix all heading styles, reformat all tables, update page numbering.
- **Error-prone**: Humans miss things in 1000-page documents. The more pages, the more drift, the more inconsistency.
- **Time-sensitive**: Legal deadlines are hard. Pharmaceutical submission windows are narrow. A document that needs 200 precise edits and it's due in 4 hours.

A frontier LLM like GPT-4o or Claude can *decide* what edits need to be made — "replace all instances of 'Acme Corp' with 'Vertex Partners' in the party definitions" — but it cannot *execute* those edits reliably on a 2000-page XML document because:

1. **Context window limits**: Even with 200k tokens, a 2000-page DOCX XML can be 10M+ tokens
2. **Precision degrades**: LLMs hallucinate on repetitive find-replace tasks at scale
3. **Cost**: Running a frontier model on 10M tokens for mechanical edits is absurdly expensive
4. **Speed**: Waiting 2 minutes per edit on a $0.50/call when you have 200 edits = $100 and 6+ hours

This is where the **applicator model** comes in.

---

## 1. The Legal Domain

### 1.1 Contract Redlining

**What happens**: Two parties negotiate a contract. Party A sends a draft. Party B's lawyers review it and produce a redlined version — deletions shown in red strikethrough, additions shown in blue/green, comments in margin bubbles.

**Real files**: 50-500 pages. Employment agreements, M&A purchase agreements, licensing deals, NDAs, lease agreements. The DOCX XML contains:
- `<w:del>` tags for deletions (redline)
- `<w:ins>` tags for insertions (redline)
- `<w:commentRangeStart>` / `<w:commentRangeEnd>` for comments
- `<w:rPr>` with `<w:strike/>` for strikethrough
- `<w:highlight w:val="yellow"/>` for highlighting
- Complex nested runs (`<w:r>`) within paragraphs (`<w:p>`)

**What the applicator model needs to do**:
- Accept/reject specific tracked changes
- Apply a list of redline edits: "In Section 3.2, change 'shall' to 'may'"
- Add comments to specific text ranges
- Highlight clauses that need attention
- Change party names throughout (but only in defined terms, not in boilerplate)
- Renumber sections after insertions/deletions

**Why frontier models fail here**: The XML for a single redlined paragraph can be 500+ tokens because of nested formatting runs. A 200-page contract has ~4000 paragraphs = ~2M tokens of XML. No frontier model can hold this and make precise character-level edits.

### 1.2 Affidavits and Court Filings

**What happens**: A lawyer drafts an affidavit (sworn statement). It gets revised 10+ times. Each revision needs precise changes: updating dates, correcting citations, reformatting numbered paragraphs, ensuring consistent caption blocks.

**Real files**: 10-100 pages but extremely format-sensitive. Court rules dictate exact margins, font sizes (usually Times New Roman 12pt), line spacing (double), page numbering format. A filing that doesn't match the court's formatting rules gets rejected.

**What the applicator model needs to do**:
- Fix margin inconsistencies (court rules say 1" margins, PDF-to-DOCX conversion broke them)
- Ensure all paragraphs are double-spaced (some imported as single-spaced)
- Fix page numbering (restart after cover page, roman numerals for TOC, arabic for body)
- Fix indentation of numbered paragraphs (1., a., i., etc. — each level has specific indent)
- Replace placeholder text: "[CLIENT NAME]" → "Johnson & Johnson"
- Fix citation formatting: "Smith v. Jones, 123 F.3d 456" — ensure italics on case names

### 1.3 Case Files and Discovery Documents

**What happens**: In litigation, parties exchange millions of pages of documents. These are often scanned PDFs converted to DOCX for review. The conversion introduces massive artifacts:
- OCR errors: "the" becomes "tbe", "I" becomes "l", "0" becomes "O"
- Binary image blobs interspersed with text (scanned letterheads, signatures, stamps)
- Broken tables (cells merged incorrectly, borders missing)
- Headers/footers from the original document appear as body text
- Page breaks in wrong places
- Weird Unicode: zero-width spaces, non-breaking hyphens, soft hyphens

**What the applicator model needs to do**:
- Clean OCR artifacts (systematic character substitution patterns)
- Identify and tag image regions vs. text regions
- Reconstruct broken tables
- Remove junk characters (zero-width spaces, control characters)
- Fix encoding issues (smart quotes → straight quotes, em-dashes → hyphens where appropriate)
- Re-establish proper paragraph boundaries (merged paragraphs, split paragraphs)

---

## 2. The Pharmaceutical Domain

### 2.1 Regulatory Submissions (IND/NDA/ANDA)

**What happens**: Pharmaceutical companies submit applications to the FDA (US), EMA (EU), CDSCO (India) for drug approval. These submissions are **massive** — a New Drug Application (NDA) can be 100,000+ pages across multiple volumes.

**Common Technical Document (CTD) structure**:
- Module 1: Administrative (regional, 100-500 pages)
- Module 2: Summaries (200-500 pages)
- Module 3: Quality (manufacturing, 1000-5000 pages)
- Module 4: Nonclinical (animal studies, 2000-10000 pages)
- Module 5: Clinical (human trials, 10000-50000 pages)

**What the applicator model needs to do**:
- Update drug names throughout (when generic name changes during review)
- Replace dosage information across all modules when formulation changes
- Update cross-references when sections are added/removed
- Fix table formatting (clinical trial data tables are extremely complex)
- Ensure consistent terminology (the FDA is strict about drug name consistency)
- Apply revision marks showing what changed between submission versions
- Update headers/footers with correct module/section numbers

### 2.2 Drug Labels and Package Inserts

**What happens**: The FDA-approved drug label (package insert) is a highly structured document with mandated sections: Indications, Dosage, Warnings, Adverse Reactions, etc. Any change requires a "labeling supplement" with precise tracked changes.

**Real files**: 20-80 pages, but every character matters. The label is the legal document that governs how a drug can be marketed and prescribed.

**What the applicator model needs to do**:
- Add new adverse reactions to the correct section (maintaining alphabetical order within severity categories)
- Update boxed warnings (the most serious safety warnings, formatted with specific border rules)
- Change dosage recommendations with correct track-changes markup
- Ensure table formatting matches FDA guidance (specific column widths, header styles)
- Cross-reference updates ("see Section 5.2" — section numbers shift when content is added)

### 2.3 Clinical Study Reports (CSR)

**What happens**: After a clinical trial, a Clinical Study Report is written — typically 200-2000 pages, heavily formatted with tables, figures, and appendices. These documents go through 10+ revision cycles.

**What the applicator model needs to do**:
- Replace investigator names when sites are added/removed
- Update statistical tables (new data = new numbers everywhere)
- Fix figure numbering (Figure 1, Figure 2... when figures are reordered)
- Maintain consistent formatting across sections (different authors write different sections)
- Apply company style guide rules (specific heading formats, table styles, figure caption formats)

---

## 3. Common Patterns Across Both Domains

### 3.1 The PDF-to-DOCX Conversion Nightmare

Most real-world document editing starts with: **"Here's a PDF, make it editable."**

PDF-to-DOCX conversion (via Adobe, LibreOffice, or online tools) produces DOCX files that are technically valid but structurally horrifying:

```xml
<!-- What the original DOCX paragraph looks like -->
<w:p>
  <w:r><w:t>This is a normal paragraph with consistent formatting.</w:t></w:r>
</w:p>

<!-- What the same paragraph looks like after PDF→DOCX conversion -->
<w:p>
  <w:r><w:rPr><w:sz w:val="24"/><w:spacing w:val="-2"/></w:rPr><w:t>Th</w:t></w:r>
  <w:r><w:rPr><w:sz w:val="24"/><w:spacing w:val="0"/></w:rPr><w:t>is </w:t></w:r>
  <w:r><w:rPr><w:sz w:val="24"/><w:spacing w:val="-1"/></w:rPr><w:t>is a </w:t></w:r>
  <w:r><w:rPr><w:sz w:val="24"/><w:spacing w:val="-2"/></w:rPr><w:t>nor</w:t></w:r>
  <w:r><w:rPr><w:sz w:val="24"/><w:spacing w:val="0"/></w:rPr><w:t>mal </w:t></w:r>
  <w:r><w:rPr><w:sz w:val="24"/><w:spacing w:val="-1"/></w:rPr><w:t>par</w:t></w:r>
  <w:r><w:rPr><w:sz w:val="24"/></w:rPr><w:t>agr</w:t></w:r>
  <w:r><w:rPr><w:sz w:val="24"/><w:spacing w:val="-2"/></w:rPr><w:t>aph</w:t></w:r>
  <!-- ... 15 more runs for the rest of the sentence ... -->
</w:p>
```

**Every word — sometimes every 2-3 characters — is in its own XML run** with slightly different spacing values. This is because PDF is a visual format (absolute positioning) while DOCX is a logical format (paragraph flow). The conversion tool creates a separate run for every character position change.

**The applicator model must handle this**: It can't just do a simple find-replace on "paragraph" because the word is split across `<w:r>` runs. It needs to:
1. Recognize that fragmented runs constitute a single word
2. Consolidate runs where possible (merge adjacent runs with same formatting)
3. Perform edits that respect the run structure

### 3.2 Binary Image Blobs

Real DOCX files contain images as Base64-encoded binary data in the XML:

```xml
<w:drawing>
  <wp:inline>
    <a:graphic>
      <a:graphicData>
        <pic:pic>
          <pic:blipFill>
            <a:blip r:embed="rId7"/>
          </pic:blipFill>
        </pic:pic>
      </a:graphicData>
    </a:graphic>
  </wp:inline>
</w:drawing>
```

And in the related `word/media/` directory, the actual image file (PNG/JPEG) exists. In the OOXML relationships file, `rId7` maps to `word/media/image1.png`.

For our purposes, we simulate this as:

```xml
<image id="img_001" alt="Company Logo" format="png" size="45KB">
  iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAW...
</image>
```

**The applicator model needs to**: recognize image boundaries, not corrupt them during text edits, and potentially swap one image reference for another.

### 3.3 Junk Characters and Encoding Issues

Real documents from PDF conversion contain:
- `\u200b` (zero-width space) — invisible but breaks search/replace
- `\u00a0` (non-breaking space) — looks like a space but isn't
- `\u00ad` (soft hyphen) — invisible hyphenation hint
- `\ufeff` (BOM / zero-width no-break space) — invisible garbage
- `\u2018` `\u2019` (smart single quotes) — sometimes need normalization
- `\u2013` `\u2014` (en-dash, em-dash) — sometimes need to be plain hyphens
- `\r\n` vs `\n` vs `\r` — line ending inconsistencies
- Control characters: `\x00`–`\x1f` — OCR noise
- `\t` tabs where spaces should be, or vice versa

### 3.4 Complex Formatting Stack

A real DOCX paragraph's formatting includes:
- **Font**: family, size, bold, italic, underline, strikethrough, color, highlight
- **Paragraph**: alignment (left/center/right/justify), indent (left/right/first-line/hanging), spacing (before/after/line), line spacing (single/1.5/double/exact)
- **Borders**: top/bottom/left/right, style, width, color
- **Numbering**: list level, restart, format (1/a/i/bullet)
- **Section**: page size, margins, orientation, columns, headers/footers
- **Track changes**: insertions, deletions, formatting changes, each with author/date metadata

---

## 4. Scale and Performance Requirements

| Metric | Small Doc | Medium Doc | Large Doc | Mega Doc |
|--------|-----------|------------|-----------|----------|
| Pages | 5-20 | 20-100 | 100-500 | 500-2000+ |
| Paragraphs | 20-100 | 100-500 | 500-2000 | 2000-10000+ |
| XML tokens | 5K-20K | 20K-100K | 100K-500K | 500K-5M+ |
| Typical edits | 2-10 | 10-50 | 50-200 | 200-1000+ |
| Time budget | Seconds | Minutes | 10-30 min | 1-4 hours |
| Cost target (applicator) | $0.001 | $0.01 | $0.05 | $0.10 |
| Cost (frontier model) | $0.50 | $5.00 | $50.00 | $500+ |

The cost ratio between an applicator model and a frontier model is **500x-5000x** for mechanical edits. This is the economic case for training a specialized editing agent.

### Why frontier models can't do this alone:

1. **Context window**: 2000-page documents exceed all current context windows when represented as XML
2. **Precision at scale**: GPT-4o's accuracy on character-level edits degrades after ~50 edits in a session
3. **Cost**: $500 per document is not viable for law firms processing 100+ documents/week
4. **Latency**: 2+ hours of API calls vs. seconds for a specialized model running locally
5. **Consistency**: Frontier models don't guarantee that edit #200 follows the same pattern as edit #1

### How the applicator model solves this:

The applicator model is small (1B-7B parameters), fast, and specialized. It:
- Takes a **specific edit instruction** (from the frontier model or a human) + a **document chunk**
- Outputs the **exact modified chunk**
- Runs locally or on cheap GPU inference
- Handles one edit at a time with near-perfect accuracy
- Can process 1000 edits in minutes, not hours

---

## 5. Why an RL Environment is the Right Training Approach

Supervised fine-tuning (SFT) alone is insufficient because:

1. **Edit diversity**: There are infinite combinations of document states × edit instructions × corruption patterns. You can't pre-collect enough (input, output) pairs.
2. **Multi-step reasoning**: Some edits require multiple operations (consolidate runs, then replace, then reformat). RL learns sequences of actions, not just input→output.
3. **Error recovery**: The model needs to learn what to do when an edit partially fails (wrong target, fragmented runs). RL's reward signal teaches recovery strategies.
4. **Tool use**: The model must learn WHICH tool to use for each situation. RL naturally teaches tool selection through reward.

The environment we're building IS the training ground. Different seeds = different documents = different corruptions = different skills to learn. The model plays thousands of "games" and gets better at editing.

---

## 6. Real-World Deployment Architecture

```
                    ┌─────────────────────────────┐
                    │   Frontier Model (GPT-4o)    │
                    │   "Decide what to edit"       │
                    │   Input: document summary     │
                    │   Output: list of edit tasks  │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │      Edit Task Queue          │
                    │  [{action: "replace",          │
                    │    target: "Acme Corp",        │
                    │    content: "Vertex Partners",  │
                    │    scope: "entire document"}]   │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │   Applicator Model (1-7B)    │
                    │   "Execute the edit"          │
                    │   Processes document chunks    │
                    │   Uses tools from toolbox      │
                    │   Fast, cheap, precise         │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │      Verifier / Grader        │
                    │   "Did the edit work?"         │
                    │   Compares before/after         │
                    │   Checks no collateral damage  │
                    └─────────────────────────────┘
```

This is exactly the architecture that Cursor, GitHub Copilot, and other AI coding tools use: a **planner** (frontier model) decides what to do, and an **applicator** (small, fast model) executes it. We're building the training environment for the applicator.
