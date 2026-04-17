# Game Version 1: Environment And Mechanics

## Design Goal

Build a planning-ready design for a **world editing game** where an agent or human repairs a corrupted structured world. The first version should preserve the strengths of the doc-edit direction:
- real-ish content,
- deterministic grading,
- scalable difficulty,
- rich navigation,
- and realistic edit actions.

The environment should feel like operating inside a living system, not just correcting typos.

## Product Thesis

The user fantasy is:
"I can enter a broken world, understand what is wrong, make targeted edits, and leave the world in a coherent state."

For V1, the world should remain mostly text-first and structured. That gives us:
- high observability,
- low implementation ambiguity,
- cheap replay,
- exact diffs,
- and straightforward baseline agents.

The world is not a flat file. It is a graph of related objects rendered through an editor.

## World Model

The underlying state should be represented as a structured graph with a document-like projection.

Suggested core objects:
- `Region`: a top-level area such as a chapter, page cluster, rulebook section, district, or subsystem.
- `Entity`: people, organizations, drugs, clauses, locations, tools, resources.
- `Node`: an editable content block such as a paragraph, heading, table row, checklist item, annotation, or rule statement.
- `Reference`: cross-links between nodes and entities.
- `Constraint`: machine-checkable requirements such as naming consistency, arithmetic consistency, formatting rules, dependency rules, or section-order rules.
- `Event`: logged changes, prior edits, corruption events, or reviewer comments.

This allows one state to be presented in multiple ways:
- outline view,
- document view,
- search results,
- entity inspector,
- issue list,
- and change history.

That matters because human and model competence often differs by representation, not only by raw intelligence.

## Core Loop

1. Generate or load a clean world state.
2. Apply a corruption program.
3. Give the player an editing interface and an objective.
4. Let the player navigate, inspect, and edit.
5. Score progress against the clean target and the rule system.
6. End when the player submits, times out, or reaches a solved threshold.

This loop supports both RL training and human studies.

## Task Shapes

V1 should support three task families.

### 1. Local Repair

The player fixes obvious local corruption.

Examples:
- misspellings,
- broken formatting,
- wrong names,
- missing rows,
- malformed references,
- duplicated blocks.

This is the easiest entry point and useful for calibration.

### 2. Consistency Repair

The player must reconcile the whole world.

Examples:
- an entity is renamed in some places but not others,
- a dosage value changes in a table but not in narrative text,
- section references point to the wrong heading,
- one system rule contradicts another,
- inventory totals no longer match subcomponents.

This is where the environment becomes meaningfully "world editing" rather than "document cleanup."

### 3. Intent-Driven Transformation

The player receives a higher-level instruction that requires many coordinated edits.

Examples:
- "Rename the supplier and update all downstream references."
- "Make the policy apply to pediatric patients only."
- "Merge District A and District B into a single region and reconcile capacities."
- "Change the effective date and update all dependent obligations."

This is the most valuable regime for model evaluation because it requires planning, search, and collateral-damage control.

## Corruption Model

The corruption engine should mix shallow and deep failures.

### Surface Corruptions

- spelling or casing errors
- punctuation damage
- broken formatting
- line or run fragmentation
- junk characters
- missing or duplicated blocks

### Structural Corruptions

- incorrect section order
- wrong heading hierarchy
- shifted table cells
- broken anchors and cross-references
- detached comments or footnotes
- merged or split entities

### Semantic Corruptions

- conflicting values across the world
- contradictions between table and prose
- stale references after renames
- impossible numeric constraints
- reviewer note not resolved in final content

### World-Specific Corruptions

If we later broaden beyond documents, these become:
- invalid dependency graph edges,
- impossible map adjacency,
- broken resource conservation,
- contradictory state transitions,
- or corrupted object metadata.

## Observation Design

The observation layer should be richer than a single viewport.

### Shared Observation Channels

- `objective`: what success looks like
- `outline`: top-level structure with jump targets
- `viewport`: current editable slice
- `search_results`: results from explicit queries
- `issue_hints`: optional system-detected anomalies for easier tasks
- `entity_panel`: metadata for current entities and references
- `progress`: similarity, rule violations, unresolved comments, remaining time

This follows the spirit of Architecture F from the v3 design, but makes the "world" explicit.

## Action Space

The action space should stay discrete and auditable.

### Navigation Actions

- jump to line / node / region
- search text
- search entity
- open reference target
- open issue
- change view mode

### Edit Actions

- replace text
- insert block
- delete block
- move block
- update entity attribute
- repair reference
- merge nodes
- split node
- set formatting
- resolve comment

### Control Actions

- request hint
- validate current state
- undo
- redo
- submit

The model API should use structured tool calls even if the human uses a GUI. That makes logs comparable.

## Reward Design

We should not rely on final exact-match alone.

Recommended score components:
- target similarity gain
- rule-violation reduction
- successful reference repair
- completion bonus
- efficiency bonus
- collateral damage penalty
- invalid action penalty
- hint usage penalty for benchmark modes

Suggested principle:
- dense reward for progress,
- sparse reward for true completion,
- strong penalty for damaging correct content.

## Difficulty Ladder

V1 should have a clean progression.

### Level 1: Visible Errors

- few corruptions
- short world
- hints enabled
- local edits only

### Level 2: Multi-Location Repair

- same fact appears in multiple places
- search becomes important
- some edits have dependencies

### Level 3: Structural Repair

- hierarchy, tables, and references matter
- wrong edits can cascade

### Level 4: Semantic Repair

- consistency across the world matters
- some failures are only visible through cross-checking

### Level 5: Intent Rewrite

- instruction changes part of the world model
- many coordinated edits
- strong potential for collateral damage

## Grading

The key requirement is that grading remains verifiable.

V1 grading should combine:
- exact structured diff against target state,
- constraint satisfaction score,
- edit precision score,
- and optional path-quality metrics.

Path-quality matters because two players may reach the same final answer very differently.
Useful path metrics:
- steps taken,
- search efficiency,
- number of undos,
- damage introduced then repaired,
- and time-to-first-correct-fix.

## Why This Is Good For Human-vs-Model Comparison

This environment reveals different strengths:
- humans are often better at global coherence and ambiguity handling,
- models are often better at repetitive local cleanup and exhaustive search,
- both struggle in different ways with interface friction.

By keeping the underlying state and grader identical, we can compare:
- accuracy,
- speed,
- damage rate,
- and strategy patterns.

That comparison is one of the most valuable outputs of the project.

## V1 Scope Recommendation

Keep the first shipped world narrow.

Recommended scope:
- document-shaped world,
- 3 task families,
- 4-6 corruption bundles,
- text-plus-structure interface,
- deterministic target state,
- exact telemetry for human and model runs.

Avoid in V1:
- free-form visual PDF editing,
- open-ended natural language grading,
- uncontrolled external tools,
- and domains that require expert knowledge just to play.

## Open Questions

- Should the hidden target always be unique, or can some tasks allow multiple valid end states?
- Do we want the human to see a natural editor while the model sees tools, or should both be constrained to the same abstractions?
- How much assistance should hints provide before we stop measuring true planning ability?
- Should task generation come from real corpora only, or mixed real-plus-synthetic content pools?
- Do we want replay review tools from day one so we can inspect human and model strategies side by side?
