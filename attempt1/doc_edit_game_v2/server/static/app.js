const modelToolExamples = {
  replace: { target: "recieve", content: "receive" },
  regex_replace: { pattern: "Acme\\s+Corp", replacement: "Vertex Partners" },
  insert: { position: 4, content: "Inserted paragraph text." },
  delete: { target: "This line does not belong" },
  move: { target: "Important Notice", position: 5 },
  format_text: { target: "Agreement", format: "bold" },
  highlight: { target: "Section 3.2", color: "yellow" },
  set_alignment: { line_index: 3, alignment: "center" },
  set_spacing: { line_index: 3, spacing_after: "24" },
  clean_junk_chars: {},
  merge_runs: { line_index: 12 },
  fix_encoding: { target: "â€\"", replacement: "—" },
  add_redline: { target: "Acme Corp", new_text: "Vertex Partners", author: "Reviewer" },
  accept_change: { change_text: "Vertex Partners" },
  reject_change: { change_text: "Acme Corp" },
  add_comment: { target: "Section 3.2", comment_text: "Check this clause", author: "Reviewer" },
  scroll_to: { chunk: 1 },
  search_forward: { query: "agreement" },
  search_backward: { query: "agreement" },
  get_overview: {},
};

const state = {
  sessionId: null,
  current: null,
  activeLane: "human",
  editors: {},
  modelDirty: false,
  humanDirty: false,
};

const els = {
  seedInput: document.getElementById("seedInput"),
  corruptionSeedInput: document.getElementById("corruptionSeedInput"),
  difficultySelect: document.getElementById("difficultySelect"),
  domainSelect: document.getElementById("domainSelect"),
  loadSeedButton: document.getElementById("loadSeedButton"),
  reloadExactSeedButton: document.getElementById("reloadExactSeedButton"),
  rerollCorruptionButton: document.getElementById("rerollCorruptionButton"),
  scenarioExposition: document.getElementById("scenarioExposition"),
  instructionText: document.getElementById("instructionText"),
  sessionId: document.getElementById("sessionId"),
  docSeed: document.getElementById("docSeed"),
  corruptionSeedValue: document.getElementById("corruptionSeedValue"),
  difficultyValue: document.getElementById("difficultyValue"),
  domainValue: document.getElementById("domainValue"),
  docTypeValue: document.getElementById("docTypeValue"),
  corruptionValue: document.getElementById("corruptionValue"),
  sourceDocumentRaw: document.getElementById("sourceDocumentRaw"),
  humanRawMarkup: document.getElementById("humanRawMarkup"),
  modelRawMarkup: document.getElementById("modelRawMarkup"),
  submitHumanButton: document.getElementById("submitHumanButton"),
  humanLiveSimilarity: document.getElementById("humanLiveSimilarity"),
  humanCompositeScore: document.getElementById("humanCompositeScore"),
  humanCollateral: document.getElementById("humanCollateral"),
  modelToolSelect: document.getElementById("modelToolSelect"),
  modelParams: document.getElementById("modelParams"),
  applyModelActionButton: document.getElementById("applyModelActionButton"),
  submitModelButton: document.getElementById("submitModelButton"),
  syncModelButton: document.getElementById("syncModelButton"),
  runModelButton: document.getElementById("runModelButton"),
  runModelMode: document.getElementById("runModelMode"),
  modelSimilarity: document.getElementById("modelSimilarity"),
  modelReward: document.getElementById("modelReward"),
  modelStepsRemaining: document.getElementById("modelStepsRemaining"),
  modelCompositeScore: document.getElementById("modelCompositeScore"),
  modelObservation: document.getElementById("modelObservation"),
  modelActivity: document.getElementById("modelActivity"),
  humanLaneTab: document.getElementById("humanLaneTab"),
  modelLaneTab: document.getElementById("modelLaneTab"),
  humanLanePanel: document.getElementById("humanLanePanel"),
  modelLanePanel: document.getElementById("modelLanePanel"),
  humanSelectionLabel: document.getElementById("humanSelectionLabel"),
  modelSelectionLabel: document.getElementById("modelSelectionLabel"),
  referenceOutline: document.getElementById("referenceOutline"),
};

function setButtonState(button, disabled, label) {
  button.disabled = disabled;
  if (label) {
    button.dataset.originalText = button.dataset.originalText || button.textContent;
    button.textContent = label;
  } else if (button.dataset.originalText) {
    button.textContent = button.dataset.originalText;
  }
}

function formatScore(value) {
  if (value === null || value === undefined) return "-";
  return Number(value).toFixed(4);
}

function randomSeed() {
  return Math.floor(Math.random() * 999_999_999) + 1;
}

function escapeHtml(text = "") {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function escapeAttribute(text = "") {
  return escapeHtml(text).replace(/"/g, "&quot;");
}

function parseAttributes(attrText = "") {
  const attrs = {};
  const pattern = /([a-zA-Z-]+)="([^"]*)"/g;
  let match;
  while ((match = pattern.exec(attrText)) !== null) {
    attrs[match[1]] = match[2];
  }
  return attrs;
}

function serializeAttributes(attrs = {}) {
  return Object.entries(attrs)
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .map(([key, value]) => ` ${key}="${escapeAttribute(String(value))}"`)
    .join("");
}

function getAttrValue(attrText, name) {
  const match = attrText.match(new RegExp(`${name}="([^"]*)"`, "i"));
  return match ? match[1] : "";
}

function normalizeColor(color = "") {
  const value = String(color).toLowerCase();
  if (value.includes("255, 255, 0") || value.includes("yellow")) return "yellow";
  if (value.includes("0, 128, 0") || value.includes("green")) return "green";
  if (value.includes("255, 0, 0") || value.includes("red")) return "red";
  if (value.includes("0, 0, 255") || value.includes("blue")) return "blue";
  return "yellow";
}

function inlineMarkupToHtml(markup = "") {
  return markup
    .replace(/<bold>/g, "<strong>")
    .replace(/<\/bold>/g, "</strong>")
    .replace(/<italic>/g, "<em>")
    .replace(/<\/italic>/g, "</em>")
    .replace(/<underline>/g, "<u>")
    .replace(/<\/underline>/g, "</u>")
    .replace(/<strike>/g, "<s>")
    .replace(/<\/strike>/g, "</s>")
    .replace(/<highlight([^>]*)>/g, (_, attrText) => {
      const color = getAttrValue(attrText, "color") || "yellow";
      return `<mark class="inline-highlight" data-color="${escapeAttribute(color)}" style="background-color:${escapeAttribute(color)};">`;
    })
    .replace(/<\/highlight>/g, "</mark>")
    .replace(/<run([^>]*)>/g, (_, attrText) => {
      const spacing = getAttrValue(attrText, "spacing") || "0";
      return `<span class="run-fragment" data-spacing="${escapeAttribute(spacing)}">`;
    })
    .replace(/<\/run>/g, "</span>")
    .replace(/<comment([^>]*)>/g, (_, attrText) => {
      const author = getAttrValue(attrText, "author");
      const text = getAttrValue(attrText, "text");
      return `<span class="inline-comment" data-author="${escapeAttribute(author)}" data-text="${escapeAttribute(text)}" title="${escapeAttribute(text)}">`;
    })
    .replace(/<\/comment>/g, "</span>")
    .replace(/<del([^>]*)>/g, (_, attrText) => {
      const author = getAttrValue(attrText, "author");
      return `<del data-author="${escapeAttribute(author)}">`;
    })
    .replace(/<ins([^>]*)>/g, (_, attrText) => {
      const author = getAttrValue(attrText, "author");
      return `<ins data-author="${escapeAttribute(author)}">`;
    });
}

function parseDocument(markup = "") {
  const lines = String(markup || "").split("\n");
  const blocks = [];

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    if (!line.trim()) {
      continue;
    }

    if (line.startsWith("<table")) {
      const startLine = i;
      const tableMatch = line.match(/^<table([^>]*)>$/);
      const tableAttrs = parseAttributes(tableMatch ? tableMatch[1] : "");
      const rows = [];
      i += 1;
      while (i < lines.length && !lines[i].startsWith("</table")) {
        const rowLine = lines[i];
        const rowMatch = rowLine.match(/^<row>([\s\S]*?)<\/row>$/);
        if (rowMatch) {
          const cells = [];
          const cellPattern = /<cell([^>]*)>([\s\S]*?)<\/cell>/g;
          let cellMatch;
          while ((cellMatch = cellPattern.exec(rowMatch[1])) !== null) {
            cells.push({
              attrs: parseAttributes(cellMatch[1]),
              content: cellMatch[2],
            });
          }
          rows.push(cells);
        }
        i += 1;
      }
      blocks.push({
        tag: "table",
        attrs: tableAttrs,
        rows,
        lineStart: startLine,
      });
      continue;
    }

    const headingMatch = line.match(/^<heading([^>]*)>([\s\S]*?)<\/heading>$/);
    if (headingMatch) {
      blocks.push({
        tag: "heading",
        attrs: parseAttributes(headingMatch[1]),
        content: headingMatch[2],
        lineStart: i,
      });
      continue;
    }

    const paragraphMatch = line.match(/^<p([^>]*)>([\s\S]*?)<\/p>$/);
    if (paragraphMatch) {
      blocks.push({
        tag: "p",
        attrs: parseAttributes(paragraphMatch[1]),
        content: paragraphMatch[2],
        lineStart: i,
      });
      continue;
    }

    blocks.push({
      tag: "p",
      attrs: { align: "left", "spacing-after": "12" },
      content: escapeHtml(line),
      lineStart: i,
    });
  }

  return blocks;
}

function applyBlockPresentation(blockEl) {
  const attrs = blockEl._docAttrs || {};
  const isHeading = blockEl.dataset.blockTag === "heading";
  const level = attrs.level || "1";

  blockEl.className = "doc-block";
  if (isHeading) {
    blockEl.classList.add("doc-heading", `level-${level}`);
  } else if (blockEl.dataset.blockTag === "table") {
    blockEl.classList.add("doc-table-wrap");
  } else {
    blockEl.classList.add("doc-paragraph");
  }

  blockEl.style.textAlign = attrs.align || "left";
  blockEl.style.marginBottom = `${Number(attrs["spacing-after"] || 12) * 1.05}px`;
  blockEl.style.textIndent = `${Number(attrs["indent-first"] || 0)}px`;
  blockEl.style.paddingLeft = `${Number(attrs["indent-left"] || 0)}px`;
  blockEl.style.lineHeight = attrs["line-spacing"] || "";
  blockEl.style.fontWeight = attrs.bold === "true" ? "700" : "";
  blockEl.style.fontStyle = attrs.italic === "true" ? "italic" : "";

  const underlined = attrs.underline && attrs.underline !== "false";
  blockEl.style.textDecoration = underlined ? "underline" : "";

  blockEl.style.borderTop = attrs["border-top"] ? `2px ${attrs["border-top"] === "double" ? "double" : "solid"} rgba(31,43,37,0.25)` : "";
  blockEl.style.borderBottom = attrs["border-bottom"] ? `2px ${attrs["border-bottom"] === "double" ? "double" : "solid"} rgba(31,43,37,0.25)` : "";
  blockEl.style.borderLeft = attrs["border-left"] ? `2px ${attrs["border-left"] === "double" ? "double" : "solid"} rgba(31,43,37,0.25)` : "";
  blockEl.style.borderRight = attrs["border-right"] ? `2px ${attrs["border-right"] === "double" ? "double" : "solid"} rgba(31,43,37,0.25)` : "";
}

function applyCellPresentation(cellEl) {
  const attrs = cellEl._docAttrs || {};
  cellEl.style.textAlign = attrs.align || "left";
  cellEl.style.fontWeight = attrs.bold === "true" ? "700" : "";
}

function createTextBlock(block, readOnly) {
  const el = document.createElement("div");
  el.dataset.blockTag = block.tag;
  el.dataset.lineStart = String(block.lineStart || 0);
  el._docAttrs = { ...block.attrs };
  el.spellcheck = false;
  if (!readOnly) {
    el.contentEditable = "true";
  }
  el.innerHTML = inlineMarkupToHtml(block.content);
  applyBlockPresentation(el);
  return el;
}

function createTableBlock(block, readOnly) {
  const wrapper = document.createElement("div");
  wrapper.dataset.blockTag = "table";
  wrapper.dataset.lineStart = String(block.lineStart || 0);
  wrapper._docAttrs = { ...block.attrs };

  const table = document.createElement("table");
  table.className = "doc-table";

  block.rows.forEach((row) => {
    const tr = document.createElement("tr");
    row.forEach((cell) => {
      const td = document.createElement("td");
      td.className = "doc-table-cell";
      td._docAttrs = { ...cell.attrs };
      if (!readOnly) {
        td.contentEditable = "true";
      }
      td.spellcheck = false;
      td.innerHTML = inlineMarkupToHtml(cell.content);
      applyCellPresentation(td);
      tr.appendChild(td);
    });
    table.appendChild(tr);
  });

  wrapper.appendChild(table);
  applyBlockPresentation(wrapper);
  return wrapper;
}

function serializeInlineChildren(node) {
  return Array.from(node.childNodes)
    .map((child) => serializeInlineNode(child))
    .join("");
}

function serializeInlineNode(node) {
  if (node.nodeType === Node.TEXT_NODE) {
    return escapeHtml(node.textContent || "");
  }

  if (node.nodeType !== Node.ELEMENT_NODE) {
    return "";
  }

  const el = node;
  const tag = el.tagName.toLowerCase();

  if (tag === "br") {
    return "";
  }

  if (el.classList.contains("run-fragment")) {
    return serializeInlineChildren(el);
  }

  let content = serializeInlineChildren(el);

  if (el.classList.contains("inline-comment")) {
    const author = el.dataset.author || "";
    const text = el.dataset.text || "";
    return `<comment author="${escapeAttribute(author)}" text="${escapeAttribute(text)}">${content}</comment>`;
  }

  if (tag === "del") {
    const author = el.dataset.author || "";
    return `<del author="${escapeAttribute(author)}">${content}</del>`;
  }

  if (tag === "ins") {
    const author = el.dataset.author || "";
    return `<ins author="${escapeAttribute(author)}">${content}</ins>`;
  }

  const style = el.style || {};
  const isBold = tag === "strong" || tag === "b" || Number(style.fontWeight || 0) >= 600;
  const isItalic = tag === "em" || tag === "i" || style.fontStyle === "italic";
  const isUnderline = tag === "u" || (style.textDecoration || "").includes("underline");
  const isStrike = tag === "s" || tag === "strike" || (style.textDecoration || "").includes("line-through");
  const hasHighlight = tag === "mark" || el.classList.contains("inline-highlight") || !!style.backgroundColor;

  if (isStrike) {
    content = `<strike>${content}</strike>`;
  }
  if (isUnderline) {
    content = `<underline>${content}</underline>`;
  }
  if (isItalic) {
    content = `<italic>${content}</italic>`;
  }
  if (isBold) {
    content = `<bold>${content}</bold>`;
  }
  if (hasHighlight) {
    const color = normalizeColor(el.dataset.color || style.backgroundColor || "yellow");
    content = `<highlight color="${escapeAttribute(color)}">${content}</highlight>`;
  }

  return content;
}

function serializeDocument(root) {
  const lines = [];
  const blocks = Array.from(root.children).filter((child) => child.classList.contains("doc-block"));

  blocks.forEach((blockEl) => {
    const attrs = blockEl._docAttrs || {};
    const tag = blockEl.dataset.blockTag;

    if (tag === "table") {
      lines.push(`<table${serializeAttributes(attrs)}>`);
      const rows = Array.from(blockEl.querySelectorAll(":scope > table > tr"));
      rows.forEach((rowEl) => {
        const cells = Array.from(rowEl.querySelectorAll(":scope > td"))
          .map((cellEl) => `<cell${serializeAttributes(cellEl._docAttrs || {})}>${serializeInlineChildren(cellEl)}</cell>`)
          .join("");
        lines.push(`<row>${cells}</row>`);
      });
      lines.push("</table>");
      return;
    }

    const content = serializeInlineChildren(blockEl);
    if (tag === "heading") {
      lines.push(`<heading${serializeAttributes(attrs)}>${content}</heading>`);
      return;
    }
    lines.push(`<p${serializeAttributes(attrs)}>${content}</p>`);
  });

  return lines.join("\n");
}

class MarkupDocumentEditor {
  constructor(root, options = {}) {
    this.root = root;
    this.readOnly = options.readOnly || false;
    this.rawOutput = options.rawOutput || null;
    this.outlineRoot = options.outlineRoot || null;
    this.selectionLabel = options.selectionLabel || null;
    this.onChange = options.onChange || (() => {});
    this.onSelectionChange = options.onSelectionChange || (() => {});
    this.selectedBlock = null;

    this.root.addEventListener("click", (event) => this.handleClick(event));
    this.root.addEventListener("focusin", (event) => this.handleFocusIn(event));
    this.root.addEventListener("input", (event) => this.handleInput(event));
    this.root.addEventListener("keydown", (event) => this.handleKeyDown(event));
  }

  setDocument(markup) {
    const blocks = parseDocument(markup);
    this.root.innerHTML = "";
    blocks.forEach((block) => {
      const element = block.tag === "table" ? createTableBlock(block, this.readOnly) : createTextBlock(block, this.readOnly);
      this.root.appendChild(element);
    });
    this.updateRawOutput();
    this.updateOutline();
    this.selectBlock(this.root.querySelector(".doc-block"));
  }

  getDocument() {
    return serializeDocument(this.root);
  }

  getBlocks() {
    return Array.from(this.root.querySelectorAll(":scope > .doc-block"));
  }

  getSelectedBlock() {
    return this.selectedBlock;
  }

  getSelectionMeta() {
    const block = this.selectedBlock;
    if (!block) {
      return {
        label: "None",
        blockType: "p",
        alignment: "left",
        spacing: "12",
        indent: "0",
      };
    }

    const attrs = block._docAttrs || {};
    const order = this.getBlocks().indexOf(block) + 1;
    let blockType = block.dataset.blockTag;
    if (blockType === "heading") {
      blockType = `heading-${attrs.level || "1"}`;
    }
    return {
      label: `${block.dataset.blockTag === "table" ? "Table" : blockType.replace("-", " ")} · block ${order}`,
      blockType,
      alignment: attrs.align || "left",
      spacing: attrs["spacing-after"] || "12",
      indent: attrs["indent-first"] || "0",
    };
  }

  selectBlock(block) {
    this.getBlocks().forEach((candidate) => candidate.classList.remove("is-selected"));
    this.selectedBlock = block || null;
    if (this.selectedBlock) {
      this.selectedBlock.classList.add("is-selected");
    }
    const meta = this.getSelectionMeta();
    if (this.selectionLabel) {
      this.selectionLabel.textContent = meta.label;
    }
    this.onSelectionChange(meta);
  }

  updateRawOutput() {
    if (this.rawOutput) {
      this.rawOutput.value = this.getDocument();
    }
  }

  updateOutline() {
    if (!this.outlineRoot) return;
    this.outlineRoot.innerHTML = "";

    const headingBlocks = this.getBlocks()
      .map((block, index) => ({ block, index }))
      .filter(({ block }) => block.dataset.blockTag === "heading");

    if (!headingBlocks.length) {
      const empty = document.createElement("div");
      empty.className = "empty-state";
      empty.textContent = "No headings found in this document.";
      this.outlineRoot.appendChild(empty);
      return;
    }

    headingBlocks.forEach(({ block, index }) => {
      const attrs = block._docAttrs || {};
      const button = document.createElement("button");
      button.type = "button";
      button.className = "outline-item";
      button.innerHTML = `<span>${block.textContent.trim() || "Untitled heading"}</span><small>Level ${attrs.level || "1"}</small>`;
      button.addEventListener("click", () => {
        block.scrollIntoView({ behavior: "smooth", block: "center" });
        this.selectBlock(block);
      });
      this.outlineRoot.appendChild(button);
    });
  }

  handleClick(event) {
    const block = event.target.closest(".doc-block");
    if (block) {
      this.selectBlock(block);
    }
  }

  handleFocusIn(event) {
    const block = event.target.closest(".doc-block");
    if (block) {
      this.selectBlock(block);
    }
  }

  handleInput(event) {
    if (!event.target.closest(".doc-block")) return;
    this.updateRawOutput();
    this.updateOutline();
    this.onChange(this.getDocument());
  }

  handleKeyDown(event) {
    if (this.readOnly) return;
    const block = event.target.closest(".doc-block");
    if (!block) return;
    if (event.key === "Enter" && !event.shiftKey && !event.target.closest(".doc-table-cell")) {
      event.preventDefault();
      this.addParagraphAfter(block);
    }
  }

  applyInline(command) {
    if (this.readOnly) return;
    const focused = document.activeElement && this.root.contains(document.activeElement) ? document.activeElement : this.selectedBlock;
    if (!focused) return;

    focused.focus();
    if (command === "bold") {
      document.execCommand("bold");
    } else if (command === "italic") {
      document.execCommand("italic");
    } else if (command === "underline") {
      document.execCommand("underline");
    } else if (command === "highlight") {
      document.execCommand("hiliteColor", false, "yellow");
    } else if (command === "remove") {
      document.execCommand("removeFormat");
    }

    window.setTimeout(() => {
      this.updateRawOutput();
      this.onChange(this.getDocument());
    }, 0);
  }

  applyBlockType(value) {
    const block = this.selectedBlock;
    if (!block || block.dataset.blockTag === "table") return;

    if (value.startsWith("heading-")) {
      block.dataset.blockTag = "heading";
      block._docAttrs.level = value.split("-")[1];
    } else {
      block.dataset.blockTag = "p";
      delete block._docAttrs.level;
    }
    applyBlockPresentation(block);
    this.updateRawOutput();
    this.updateOutline();
    this.selectBlock(block);
    this.onChange(this.getDocument());
  }

  applyBlockAttribute(name, value) {
    const block = this.selectedBlock;
    if (!block || block.dataset.blockTag === "table") return;

    if (name === "align") {
      block._docAttrs.align = value;
    }
    if (name === "spacing-after") {
      block._docAttrs["spacing-after"] = value;
    }
    if (name === "indent-first") {
      if (value === "0") {
        delete block._docAttrs["indent-first"];
      } else {
        block._docAttrs["indent-first"] = value;
      }
    }
    applyBlockPresentation(block);
    this.updateRawOutput();
    this.selectBlock(block);
    this.onChange(this.getDocument());
  }

  addParagraphAfter(referenceBlock = this.selectedBlock) {
    if (this.readOnly) return;
    const newBlock = createTextBlock(
      {
        tag: "p",
        attrs: { align: "justify", "spacing-after": "12", "indent-first": "36" },
        content: "New paragraph.",
      },
      false
    );

    if (!referenceBlock || !referenceBlock.parentElement) {
      this.root.appendChild(newBlock);
    } else {
      referenceBlock.after(newBlock);
    }

    this.updateRawOutput();
    this.updateOutline();
    this.selectBlock(newBlock);
    newBlock.focus();
    this.onChange(this.getDocument());
  }

  moveSelectedBlock(direction) {
    if (this.readOnly || !this.selectedBlock) return;
    const sibling = direction < 0 ? this.selectedBlock.previousElementSibling : this.selectedBlock.nextElementSibling;
    if (!sibling) return;

    if (direction < 0) {
      sibling.before(this.selectedBlock);
    } else {
      sibling.after(this.selectedBlock);
    }
    this.updateRawOutput();
    this.updateOutline();
    this.selectBlock(this.selectedBlock);
    this.onChange(this.getDocument());
  }

  deleteSelectedBlock() {
    if (this.readOnly || !this.selectedBlock) return;
    const blocks = this.getBlocks();
    if (blocks.length <= 1) return;
    const nextBlock = this.selectedBlock.nextElementSibling || this.selectedBlock.previousElementSibling;
    this.selectedBlock.remove();
    this.updateRawOutput();
    this.updateOutline();
    this.selectBlock(nextBlock);
    this.onChange(this.getDocument());
  }
}

function updateEditorControls(editorKey, meta) {
  const prefix = editorKey === "human" ? "human" : "model";
  const blockType = document.getElementById(`${prefix}BlockType`);
  const alignment = document.getElementById(`${prefix}Alignment`);
  const spacing = document.getElementById(`${prefix}Spacing`);
  const indent = document.getElementById(`${prefix}Indent`);
  const isTable = meta.blockType === "table";

  if (blockType) {
    blockType.disabled = isTable;
    blockType.value = isTable ? "p" : meta.blockType;
  }
  if (alignment) {
    alignment.disabled = isTable;
    alignment.value = meta.alignment;
  }
  if (spacing) {
    spacing.disabled = isTable;
    spacing.value = meta.spacing;
  }
  if (indent) {
    indent.disabled = isTable;
    indent.value = meta.indent;
  }
}

function bindEditorControls(editorKey) {
  const editor = state.editors[editorKey];
  const prefix = editorKey === "human" ? "human" : "model";

  document.querySelectorAll(`[data-editor="${editorKey}"][data-inline]`).forEach((button) => {
    button.addEventListener("mousedown", (event) => event.preventDefault());
    button.addEventListener("click", () => editor.applyInline(button.dataset.inline));
  });

  document.getElementById(`${prefix}BlockType`).addEventListener("change", (event) => {
    editor.applyBlockType(event.target.value);
  });
  document.getElementById(`${prefix}Alignment`).addEventListener("change", (event) => {
    editor.applyBlockAttribute("align", event.target.value);
  });
  document.getElementById(`${prefix}Spacing`).addEventListener("change", (event) => {
    editor.applyBlockAttribute("spacing-after", event.target.value);
  });
  document.getElementById(`${prefix}Indent`).addEventListener("change", (event) => {
    editor.applyBlockAttribute("indent-first", event.target.value);
  });
  document.getElementById(`${prefix}AddParagraph`).addEventListener("click", () => editor.addParagraphAfter());
  document.getElementById(`${prefix}MoveUp`).addEventListener("click", () => editor.moveSelectedBlock(-1));
  document.getElementById(`${prefix}MoveDown`).addEventListener("click", () => editor.moveSelectedBlock(1));
  document.getElementById(`${prefix}DeleteBlock`).addEventListener("click", () => editor.deleteSelectedBlock());
}

function populateToolSelect() {
  Object.keys(modelToolExamples).forEach((tool) => {
    const option = document.createElement("option");
    option.value = tool;
    option.textContent = tool;
    els.modelToolSelect.appendChild(option);
  });
  els.modelToolSelect.value = "replace";
  applyToolTemplate();
}

function applyToolTemplate() {
  const tool = els.modelToolSelect.value;
  els.modelParams.value = JSON.stringify(modelToolExamples[tool] || {}, null, 2);
}

function renderHumanScores(current) {
  els.humanLiveSimilarity.textContent = formatScore(current.human_similarity_live);
  els.humanCompositeScore.textContent = current.human_result
    ? formatScore(current.human_result.composite_score)
    : "-";
  els.humanCollateral.textContent = current.human_result
    ? formatScore(current.human_result.collateral_damage)
    : "-";
}

function renderModelActivity(activity = []) {
  els.modelActivity.innerHTML = "";
  if (!activity.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "No model activity yet.";
    els.modelActivity.appendChild(empty);
    return;
  }

  activity
    .slice()
    .reverse()
    .forEach((entry) => {
      const item = document.createElement("article");
      item.className = "activity-item";
      item.innerHTML = `
        <div class="activity-meta">
          <span class="activity-kind">${entry.kind || "event"}</span>
          <span>step ${entry.step ?? 0}</span>
          <span>sim ${formatScore(entry.similarity)}</span>
        </div>
        <div>${entry.summary || ""}</div>
      `;
      els.modelActivity.appendChild(item);
    });
}

function renderModel(current, replaceEditor = true) {
  const obs = current.model_observation;

  if (replaceEditor) {
    state.editors.model.setDocument(obs.current_document || "");
  } else {
    state.editors.model.updateRawOutput();
  }

  els.modelSimilarity.textContent = formatScore(obs.similarity);
  els.modelReward.textContent = formatScore(obs.reward);
  els.modelStepsRemaining.textContent = `${obs.steps_remaining}`;
  els.modelCompositeScore.textContent = current.model_result
    ? formatScore(current.model_result.composite_score)
    : "-";
  els.modelObservation.textContent = JSON.stringify(
    {
      instruction: obs.edit_instruction,
      doc_type: obs.doc_type,
      domain: obs.domain,
      chunk_index: obs.chunk_index,
      total_chunks: obs.total_chunks,
      overview: obs.document_overview,
      steps_remaining: obs.steps_remaining,
      collateral_damage: obs.collateral_damage,
      last_tool_success: obs.last_tool_success,
      current_chunk: obs.document_chunk,
    },
    null,
    2
  );
  renderModelActivity(current.model_activity || []);
}

function renderGame(payload) {
  state.current = payload;
  state.sessionId = payload.session_id;
  state.modelDirty = false;
  state.humanDirty = false;

  els.seedInput.value = payload.doc_seed;
  els.corruptionSeedInput.value = payload.corruption_seed;
  els.scenarioExposition.textContent = payload.scenario_exposition;
  els.instructionText.textContent = payload.instruction;
  els.sessionId.textContent = payload.session_id;
  els.docSeed.textContent = payload.doc_seed;
  els.corruptionSeedValue.textContent = payload.corruption_seed;
  els.difficultyValue.textContent = `${payload.difficulty} · ${payload.difficulty_name}`;
  els.domainValue.textContent = payload.domain;
  els.docTypeValue.textContent = payload.doc_type;
  els.corruptionValue.textContent = `${payload.corruption_count} · ${payload.corruption_types.join(", ")}`;
  els.sourceDocumentRaw.value = payload.source_document;

  state.editors.reference.setDocument(payload.source_document);
  state.editors.human.setDocument(payload.human_document);
  renderHumanScores(payload);
  renderModel(payload, true);
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Request failed: ${response.status}`);
  }
  return response.json();
}

async function loadGame(mode = "random") {
  setButtonState(els.loadSeedButton, true, "Loading...");
  setButtonState(els.reloadExactSeedButton, true, "Loading...");
  setButtonState(els.rerollCorruptionButton, true, "Loading...");
  try {
    const seedValue = els.seedInput.value.trim();
    const corruptionSeedValue = els.corruptionSeedInput.value.trim();
    const useCurrentSeed = mode === "exact";
    const rerollCorruption = mode === "reroll-corruption";
    const payload = {
      seed: (useCurrentSeed || rerollCorruption) && seedValue ? Number(seedValue) : null,
      corruption_seed: useCurrentSeed
        ? (corruptionSeedValue ? Number(corruptionSeedValue) : null)
        : rerollCorruption
          ? randomSeed()
          : null,
      difficulty: Number(els.difficultySelect.value),
      domain: els.domainSelect.value,
    };
    const data = await postJson("/api/game/new", payload);
    renderGame(data);
  } catch (error) {
    alert(`Could not load a game.\n\n${error.message}`);
  } finally {
    setButtonState(els.loadSeedButton, false);
    setButtonState(els.reloadExactSeedButton, false);
    setButtonState(els.rerollCorruptionButton, false);
  }
}

async function submitHumanDraft() {
  if (!state.sessionId) return;
  setButtonState(els.submitHumanButton, true, "Scoring...");
  try {
    const editedDocument = state.editors.human.getDocument();
    const data = await postJson(`/api/game/${state.sessionId}/submit-human`, {
      edited_document: editedDocument,
    });
    state.current.human_document = editedDocument;
    state.current.human_result = data.result;
    state.current.human_similarity_live = data.live_similarity;
    state.humanDirty = false;
    renderHumanScores(state.current);
  } catch (error) {
    alert(`Could not submit human draft.\n\n${error.message}`);
  } finally {
    setButtonState(els.submitHumanButton, false);
  }
}

async function syncModelDraft(options = {}) {
  if (!state.sessionId) return null;
  if (!state.modelDirty && !options.force) return null;

  const editedDocument = state.editors.model.getDocument();
  const data = await postJson(`/api/game/${state.sessionId}/model-draft`, {
    edited_document: editedDocument,
  });
  state.current.model_observation = data.observation;
  state.current.model_result = data.result;
  state.current.model_activity = data.activity || [];
  state.modelDirty = false;
  renderModel(state.current, true);
  return data;
}

async function applyModelTool() {
  if (!state.sessionId) return;
  setButtonState(els.applyModelActionButton, true, "Applying...");
  try {
    await syncModelDraft();
    const params = JSON.parse(els.modelParams.value || "{}");
    const data = await postJson(`/api/game/${state.sessionId}/model-step`, {
      tool: els.modelToolSelect.value,
      params,
    });
    state.current.model_observation = data.observation;
    state.current.model_result = data.result;
    state.current.model_activity = data.activity || [];
    renderModel(state.current, true);
  } catch (error) {
    alert(`Could not apply model tool.\n\n${error.message}`);
  } finally {
    setButtonState(els.applyModelActionButton, false);
  }
}

async function runModel() {
  if (!state.sessionId) return;
  setButtonState(els.runModelButton, true, "Running...");
  try {
    await syncModelDraft();
    const data = await postJson(`/api/game/${state.sessionId}/run-model`, {
      mode: els.runModelMode.value,
      max_actions: 8,
    });
    state.current.model_observation = data.observation;
    state.current.model_result = data.result;
    state.current.model_activity = data.activity || [];
    renderModel(state.current, true);
  } catch (error) {
    alert(`Could not run the model lane.\n\n${error.message}`);
  } finally {
    setButtonState(els.runModelButton, false);
  }
}

async function submitModelDraft() {
  if (!state.sessionId) return;
  setButtonState(els.submitModelButton, true, "Scoring...");
  try {
    await syncModelDraft();
    const data = await postJson(`/api/game/${state.sessionId}/submit-model`, {});
    state.current.model_result = data.result;
    state.current.model_observation = data.observation;
    state.current.model_activity = data.activity || [];
    renderModel(state.current, true);
  } catch (error) {
    alert(`Could not submit model draft.\n\n${error.message}`);
  } finally {
    setButtonState(els.submitModelButton, false);
  }
}

function setActiveLane(lane) {
  state.activeLane = lane;
  const isHuman = lane === "human";
  els.humanLaneTab.classList.toggle("is-active", isHuman);
  els.modelLaneTab.classList.toggle("is-active", !isHuman);
  els.humanLanePanel.classList.toggle("is-active", isHuman);
  els.modelLanePanel.classList.toggle("is-active", !isHuman);
}

function initializeEditors() {
  state.editors.reference = new MarkupDocumentEditor(document.getElementById("referenceEditor"), {
    readOnly: true,
    rawOutput: els.sourceDocumentRaw,
    outlineRoot: els.referenceOutline,
  });

  state.editors.human = new MarkupDocumentEditor(document.getElementById("humanEditor"), {
    rawOutput: els.humanRawMarkup,
    selectionLabel: els.humanSelectionLabel,
    onChange: () => {
      state.humanDirty = true;
      state.current = state.current || {};
      state.current.human_document = state.editors.human.getDocument();
      els.humanCompositeScore.textContent = "-";
      els.humanCollateral.textContent = "-";
    },
    onSelectionChange: (meta) => updateEditorControls("human", meta),
  });

  state.editors.model = new MarkupDocumentEditor(document.getElementById("modelEditor"), {
    rawOutput: els.modelRawMarkup,
    selectionLabel: els.modelSelectionLabel,
    onChange: () => {
      state.modelDirty = true;
      els.modelCompositeScore.textContent = "-";
    },
    onSelectionChange: (meta) => updateEditorControls("model", meta),
  });

  bindEditorControls("human");
  bindEditorControls("model");
}

els.loadSeedButton.addEventListener("click", () => loadGame("random"));
els.reloadExactSeedButton.addEventListener("click", () => loadGame("exact"));
els.rerollCorruptionButton.addEventListener("click", () => loadGame("reroll-corruption"));
els.submitHumanButton.addEventListener("click", submitHumanDraft);
els.applyModelActionButton.addEventListener("click", applyModelTool);
els.submitModelButton.addEventListener("click", submitModelDraft);
els.syncModelButton.addEventListener("click", async () => {
  setButtonState(els.syncModelButton, true, "Syncing...");
  try {
    await syncModelDraft({ force: true });
  } catch (error) {
    alert(`Could not sync manual rewrite.\n\n${error.message}`);
  } finally {
    setButtonState(els.syncModelButton, false);
  }
});
els.runModelButton.addEventListener("click", runModel);
els.modelToolSelect.addEventListener("change", applyToolTemplate);
els.humanLaneTab.addEventListener("click", () => setActiveLane("human"));
els.modelLaneTab.addEventListener("click", () => setActiveLane("model"));

initializeEditors();
populateToolSelect();
setActiveLane("human");
loadGame("random");
