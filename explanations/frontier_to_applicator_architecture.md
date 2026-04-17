# Frontier Model -> Applicator Model

This document explains the architecture we have been circling around:

- a **frontier model** like `GPT-5.4`
- a smaller **applicator model**
- a document editing task where precision matters more than free-form rewriting

The goal is to make this understandable without assuming deep ML background.

---

## 1. The Core Idea

There are really two different jobs in this system.

### Job A: understand the whole document and the instruction

This is what a frontier model is good at.

Examples:
- read a long document
- understand a complex instruction
- notice exceptions and edge cases
- decide what should change and what should not

### Job B: apply the changes very precisely

This is what an applicator model should be good at.

Examples:
- change only the exact pieces that need changing
- preserve formatting
- avoid collateral damage
- apply many edits cheaply and consistently

So the architecture is:

1. **frontier model plans**
2. **applicator executes**

---

## 2. Why Not Just Use The Frontier Model For Everything?

Because it is expensive and often too unconstrained.

If the frontier model rewrites the whole document:
- it can be very strong
- but it may touch more than needed
- it is expensive for repeated edits
- it is not the cleanest way to build a specialized editing system

What we want instead is:
- frontier model for reasoning
- applicator model for execution

That gives us:
- better cost efficiency
- more control
- a cleaner research story

---

## 3. Why Not Let The Applicator Think Too Much?

Because then the applicator becomes another general agent, which defeats the point.

An applicator model should not need to:
- inspect the entire document in many complicated ways
- call dozens of helper tools
- do high-level planning from scratch

Instead, it should receive a **structured edit plan** and carry it out.

That is why the right split is:

- frontier model = planner
- applicator = executor

---

## 4. What Language Should They Use To Talk?

Not plain English.

Plain English is flexible, but it is ambiguous.

Example:

> Move the rent clause near the end and add a signature block.

That leaves too many questions:
- exactly which rent clause?
- before which section?
- what style should the new block use?

The frontier model should instead produce a small structured edit language.

I would call it something like:

- `docpatch.v1`

It should be:
- compact
- explicit
- easy to validate
- easy for a smaller model to learn

---

## 5. The Simplest Useful Edit Language

We do **not** want 25 tiny tools.

We want a small number of strong operations.

A good first version is:

1. `replace_text`
2. `insert_after`
3. `delete_block`
4. `move_block`
5. `style_text`
6. `style_block`

That is enough to cover a surprisingly large amount of document editing.

---

## 6. Example: What The Frontier Model Produces

Suppose the instruction is:

> Replace every mention of Sanjay with Aditya, but only in paragraphs where Aditya is also mentioned.

The frontier model should not send raw prose.

It should send a plan like:

```json
{
  "version": "docpatch.v1",
  "edits": [
    {
      "op": "replace_text",
      "selector": {
        "find": "Sanjay",
        "within_block_contains": "Aditya"
      },
      "replacement": "Aditya"
    }
  ]
}
```

This is much easier for an applicator model to execute.

---

## 7. Example: Structural Edit

Suppose the instruction is:

> Move the validity clause to the top, move the rent clause before the conclusion, and add a signature block after the conclusion.

The frontier model could produce:

```json
{
  "version": "docpatch.v1",
  "edits": [
    {
      "op": "move_block",
      "anchor": {
        "quote": "Validity",
        "match": "heading_equals"
      },
      "before_anchor": {
        "quote": "__DOCUMENT_START__",
        "match": "document_start"
      }
    },
    {
      "op": "move_block",
      "anchor": {
        "quote": "Rent",
        "match": "heading_equals"
      },
      "before_anchor": {
        "quote": "Conclusion",
        "match": "heading_equals"
      }
    },
    {
      "op": "insert_after",
      "anchor": {
        "quote": "Conclusion",
        "match": "heading_equals"
      },
      "text": "Landlord Signature: ____________________\nTenant Signature: ____________________",
      "inherit_style": "previous_block"
    }
  ]
}
```

Again, the applicator does not need to invent the plan. It just needs to apply it correctly.

---

## 8. Why This Is Better Than Complete Rewrite

The complete-rewrite approach is good as a baseline because it is fast to build.

But it is not ideal for the final system.

Why?

- it edits too much at once
- it is harder to audit
- it is easier to damage formatting
- it does not match the original tool-based game design

The planner + applicator split is better because:

- the frontier model can reason globally
- the applicator can edit locally
- we can save cost
- we can train the smaller model on a narrower behavior

---

## 9. Why We Do Not Want Too Many Tools

This was the important correction in our design discussion.

If we create too many tools like:
- `get_outline`
- `get_block`
- `find_block_by_heading`
- `find_block_by_style`
- `get_match_context`
- `search_forward`
- `search_backward`

then the applicator starts behaving like a full agent.

That is not what we want.

We want:
- a frontier planner
- a smaller executor

So the frontier model should do the hard reasoning, and the applicator should use a **small edit language**.

That is simpler and more elegant.

---

## 10. Does The Applicator Need Block IDs?

Not necessarily in the user-facing interface.

Internally, the backend can assign stable IDs to paragraphs, headings, tables, and sections.

But the planner does not have to talk in terms of internal IDs.

Instead, it can use:
- anchors
- quoted text
- heading matches
- placement relative to nearby content

That is easier for the frontier model.

So:

- backend can have block IDs
- planner does not need to expose them directly

---

## 11. What The Backend Should Really Do

The backend should maintain a canonical document model.

That model can internally track:
- paragraphs
- headings
- tables
- runs
- styles
- section boundaries

Then it should apply the patch language safely to that structure.

This means:
- the frontier model does not edit raw XML
- the applicator does not need dozens of search tools
- the backend handles fidelity and document correctness

---

## 12. What The Current H200 Run Means

Right now, the H200 is running the **rewrite-based GRPO baseline**, not the final tool-policy architecture.

That run is still useful because it gives us:
- a working RL training path
- a baseline checkpoint
- a baseline comparison for later

Latest status when this note was written:
- around `48 / 100` GRPO steps completed
- `checkpoint-25` already written
- about `84 GB` VRAM in use
- about `98%` GPU utilization at the latest sample

So this is not wasted compute.

---

## 13. Should We Pause The H200 Run?

My recommendation:

### Short answer

**Do not pause immediately.**

### Why

Because:
- it is already far along
- it has started producing checkpoints
- it is using the GPU heavily
- it gives us a real rewrite-policy RL baseline

### Better stopping point

If we want to save time and pivot soon, a cleaner place to stop would be:
- after the next meaningful checkpoint
- or after the full `100` steps if the remaining time is acceptable

So my practical advice is:

- let the current rewrite-based GRPO finish if possible
- treat it as a baseline artifact
- then switch the next training cycle to the planner -> applicator architecture

---

## 14. What We Should Build Next

The next version should be:

1. `GPT-5.4` as a frontier planner
2. planner emits `docpatch.v1`
3. backend applies the patch language
4. smaller applicator model is trained to imitate or execute the same patch patterns

That gives us a much better product story:

- frontier model decides what to do
- applicator performs the edits
- cost goes down
- precision goes up

---

## 15. The Clean Mental Model

If I had to explain this in one sentence:

> The frontier model decides **what should change**, and the applicator model specializes in **changing it precisely**.

That is the architecture we should aim for.
